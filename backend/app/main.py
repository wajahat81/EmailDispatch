import os
import smtplib
import jwt
import imaplib
import email
from email.header import decode_header
import re
import asyncio
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Header, Depends, BackgroundTasks
from pydantic import BaseModel
from supabase import create_client, Client
from passlib.context import CryptContext
from dotenv import load_dotenv

load_dotenv()

# --- Environment Variables ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SENDER_EMAIL = os.getenv("SENDER_EMAIL", "system@internal.app")
RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL", "inbox@internal.app")
JWT_SECRET = os.getenv("JWT_SECRET", "super-secret-key-change-this-in-production")

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# --- Pydantic Models ---
class LoginRequest(BaseModel):
    email: str
    password: str

class EmailSendRequest(BaseModel):
    title: str
    comments: str


# --- Helper Functions ---
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def get_current_user(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid token")
    token = authorization.split(" ")[1]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

def dispatch_actual_email(sender: str, receiver: str, subject: str, body: str, log_id: str):
    msg = MIMEMultipart()
    msg['From'] = sender
    msg['To'] = receiver
    msg['Subject'] = subject
    
    # Create the Plus-Addressed Reply-To (e.g., sender+log_id@gmail.com)
    sender_name, domain = sender.split('@')
    reply_to_email = f"{sender_name}+{log_id}@{domain}"
    msg.add_header('Reply-To', reply_to_email)

    msg.attach(MIMEText(body, 'plain'))
    try:
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
    except Exception as e:
        print(f"SMTP Failed: {str(e)}")

def clean_email_body(raw_body):
    # Normalize line endings
    body = raw_body.replace('\r', '')

    # 1. Catch multi-line "On <date> <person> wrote:" blocks
    # (?is) allows the regex to match across multiple newlines seamlessly
    body = re.sub(r"(?is)\n*On\s.{1,150}?wrote:\s*\n", "\n---SPLIT---\n", body)
    
    # 2. Catch standard "Original Message" blocks
    body = re.sub(r"(?i)\n*-+\s*Original Message\s*-+\s*\n", "\n---SPLIT---\n", body)
    
    # 3. Catch Enterprise From/To blocks
    body = re.sub(r"(?i)\n*From:\s.*?\nTo:\s.*?\n", "\n---SPLIT---\n", body)

    # Split the email at the boundary
    parts = body.split("---SPLIT---")
    
    # The new reply is always the first part
    new_reply = parts[0].strip()
    
    # Clean any accidental quote markers from the reply itself
    new_reply_lines = []
    for line in new_reply.split('\n'):
        line = line.lstrip('> ').strip()
        # Remove old nested [Replied to: ...] tags to prevent stacking
        line = re.sub(r"\[Replied to:.*?\]", "", line).strip()
        if line:
            new_reply_lines.append(line)
            
    new_reply = "\n".join(new_reply_lines)
    
    # Extract the context from the previous message
    replied_to = ""
    if len(parts) > 1:
        original_text = parts[1]
        
        clean_lines = []
        for line in original_text.split('\n'):
            line = line.lstrip('> ').strip()
            
            # Filter out leftover headers
            if re.match(r"^(From|To|Subject|Date|Cc|Sent):\s", line, re.IGNORECASE):
                continue
                
            # Filter out old nested tags from the quoted text
            line = re.sub(r"\[Replied to:.*?\]", "", line).strip()
            
            if line:
                clean_lines.append(line)
        
        if clean_lines:
            quoted_text = " ".join(clean_lines)
            quoted_text = re.sub(r'\s+', ' ', quoted_text).strip()
            # Limit the quoted context to 100 characters for a clean UI
            replied_to = quoted_text[:100] + ("..." if len(quoted_text) > 100 else "")
            
    if replied_to:
        return f"{new_reply}\n\n[Replied to: {replied_to}]"
        
    return new_reply


def extract_body(msg):
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition"))
            if content_type == "text/plain" and "attachment" not in content_disposition:
                return part.get_payload(decode=True).decode(errors="ignore")
    else:
        if msg.get_content_type() == "text/plain":
            return msg.get_payload(decode=True).decode(errors="ignore")
    return ""


# --- Automated Background Sync Logic ---
def sync_imap_emails():
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(SMTP_USER, SMTP_PASSWORD)
        mail.select("inbox")

        status, messages = mail.search(None, '(UNSEEN)')
        if not messages[0]:
            mail.logout()
            return
            
        email_ids = messages[0].split()

        for e_id in email_ids:
            res, msg_data = mail.fetch(e_id, '(RFC822)')
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    
                    # Extract the Plus-Addressed ID from the "To" header
                    to_header = str(msg.get("To", ""))
                    match = re.search(r"\+([a-f0-9\-]+)@", to_header)
                    
                    # Fallback check subject for old emails just in case
                    if not match:
                        subject, encoding = decode_header(msg.get("Subject", ""))[0]
                        if isinstance(subject, bytes):
                            subject = subject.decode(encoding if encoding else "utf-8")
                        match = re.search(r"\[REF:([a-f0-9\-]+)\]", subject)

                    if match:
                        log_id = match.group(1)
                        raw_body = extract_body(msg)
                        clean_body = clean_email_body(raw_body)

                        # 1. Fetch the EXISTING response history from the database
                        current_log_res = supabase.table("email_logs").select("response_text").eq("id", log_id).execute()
                        
                        if current_log_res.data:
                            existing_history = current_log_res.data[0].get("response_text") or ""
                            
                            # 2. Combine the new reply at the top, followed by a divider, then the old history
                            if existing_history:
                                combined_response = f"{clean_body}\n\n━━━━━━━━━━━━━━━━━━━━\n\n{existing_history}"
                            else:
                                combined_response = clean_body

                            # 3. Save the combined thread back to the database
                            supabase.table("email_logs").update({
                                "response_text": combined_response[:10000] # Increased limit for long threads
                            }).eq("id", log_id).execute()

        mail.logout()
    except Exception as e:
        print(f"Background IMAP Sync Error: {e}")

async def email_sync_loop():
    while True:
        await asyncio.to_thread(sync_imap_emails)
        await asyncio.sleep(30)


# --- Application Setup ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(email_sync_loop())
    yield
    task.cancel()

app = FastAPI(title="Internal Email System API", lifespan=lifespan)


# --- Endpoints ---
@app.post("/api/create-user")
async def create_user(name: str, email: str, password: str, role: str = "employee"):
    hashed_pw = get_password_hash(password)
    res = supabase.table("profiles").insert({
        "name": name, "email": email, "password": hashed_pw, "role": role
    }).execute()
    return {"message": "User created", "user": res.data[0]}

@app.post("/api/login")
async def login(credentials: LoginRequest):
    response = supabase.table("profiles").select("*").eq("email", credentials.email).execute()
    if not response.data:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    user = response.data[0]

    if not verify_password(credentials.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token_data = {
        "id": user["id"],
        "email": user["email"],
        "name": user["name"],
        "role": user["role"],
        "exp": datetime.utcnow() + timedelta(hours=24)
    }
    token = jwt.encode(token_data, JWT_SECRET, algorithm="HS256")
    
    return {
        "access_token": token,
        "user": {"id": user["id"], "name": user["name"], "email": user["email"], "role": user["role"]}
    }

@app.get("/api/emails")
async def get_emails(user: dict = Depends(get_current_user)):
    query = supabase.table("email_logs").select("*, profiles!inner(name, email)")

    if user["role"] == "employee":
        query = query.eq("user_id", user["id"])
        
    response = query.order("created_at", desc=True).execute()
    
    formatted_data = []
    for log in response.data:
        log["sender_name"] = log["profiles"]["name"]
        log["sender_original_email"] = log["profiles"]["email"]
        formatted_data.append(log)

    return formatted_data

@app.post("/api/emails/send")
async def send_email(
    payload: EmailSendRequest, 
    background_tasks: BackgroundTasks, 
    user: dict = Depends(get_current_user)
):
    log_data = {
        "user_id": user["id"],
        "sender_email": SENDER_EMAIL,
        "receiver_email": RECEIVER_EMAIL,
        "title": payload.title,
        "comments": payload.comments
    }
    
    result = supabase.table("email_logs").insert(log_data).execute()
    log_id = result.data[0]["id"]

    background_tasks.add_task(
        dispatch_actual_email,
        sender=SENDER_EMAIL,
        receiver=RECEIVER_EMAIL,
        subject=payload.title,
        body=payload.comments, 
        log_id=log_id          
    )

    return {"status": "success"}