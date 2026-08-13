import os
import resend
import jwt
import imaplib
import email
from email.header import decode_header
import re
import asyncio
from datetime import datetime, timedelta
from typing import Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Header, Depends, BackgroundTasks
from pydantic import BaseModel
from supabase import create_client, Client
from passlib.context import CryptContext
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

# --- Environment Variables ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
JWT_SECRET = os.getenv("JWT_SECRET")  # no hardcoded fallback in production

if not JWT_SECRET:
    raise RuntimeError("JWT_SECRET environment variable is not set")

# --- Resend (outbound sending) ---
RESEND_API_KEY = os.getenv("RESEND_API_KEY")
resend.api_key = RESEND_API_KEY

FROM_EMAIL = os.getenv("FROM_EMAIL", "noreply@superwiseemails.site")
RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL", "wajahathaider12345@gmail.com")

# --- Gmail IMAP (inbound reply tracking only — NOT used for sending anymore) ---
IMAP_HOST = os.getenv("IMAP_HOST", "imap.gmail.com")
IMAP_USER = os.getenv("IMAP_USER")       # your Gmail address, e.g. wajibhai239@gmail.com
IMAP_PASSWORD = os.getenv("IMAP_PASSWORD")  # Gmail App Password (rotate the one that leaked!)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# --- Pydantic Models ---
class LoginRequest(BaseModel):
    email: str
    password: str

class EmailSendRequest(BaseModel):
    title: str
    comments: str

class CreateUserRequest(BaseModel):
    name: str
    email: str
    password: str
    role: str

class EditUserRequest(BaseModel):
    name: str
    email: str
    role: str
    password: Optional[str] = None  # Optional password change

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
    """
    Sends via Resend's API instead of raw SMTP.
    Reply-To still points to the Gmail inbox so the IMAP poller
    can catch replies and match them back to this log_id.
    """
    if not IMAP_USER:
        print("IMAP_USER not set — replies won't be trackable via Reply-To")
        reply_to_email = sender
    else:
        imap_name, imap_domain = IMAP_USER.split('@')
        reply_to_email = f"{imap_name}+{log_id}@{imap_domain}"

    try:
        resend.Emails.send({
            "from": sender,
            "to": [receiver],
            "subject": subject,
            "text": body,
            "reply_to": reply_to_email,
        })
    except Exception as e:
        print(f"Resend send failed: {str(e)}")

def clean_email_body(raw_body):
    body = raw_body.replace('\r', '')

    body = re.sub(r"(?is)\n*On\s.{1,150}?wrote:\s*\n", "\n---SPLIT---\n", body)
    body = re.sub(r"(?i)\n*-+\s*Original Message\s*-+\s*\n", "\n---SPLIT---\n", body)
    body = re.sub(r"(?i)\n*From:\s.*?\nTo:\s.*?\n", "\n---SPLIT---\n", body)

    parts = body.split("---SPLIT---")
    new_reply = parts[0].strip()

    new_reply_lines = []
    for line in new_reply.split('\n'):
        line = line.lstrip('> ').strip()
        line = re.sub(r"\[Replied to:.*?\]", "", line).strip()
        if line:
            new_reply_lines.append(line)

    new_reply = "\n".join(new_reply_lines)

    replied_to = ""
    if len(parts) > 1:
        original_text = parts[1]

        clean_lines = []
        for line in original_text.split('\n'):
            line = line.lstrip('> ').strip()
            if re.match(r"^(From|To|Subject|Date|Cc|Sent):\s", line, re.IGNORECASE):
                continue
            line = re.sub(r"\[Replied to:.*?\]", "", line).strip()
            if line:
                clean_lines.append(line)

        if clean_lines:
            quoted_text = " ".join(clean_lines)
            quoted_text = re.sub(r'\s+', ' ', quoted_text).strip()
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


# --- Automated Background Sync Logic (Gmail IMAP — unaffected by the sending fix) ---
def sync_imap_emails():
    if not IMAP_USER or not IMAP_PASSWORD:
        print("IMAP credentials not set — skipping reply sync")
        return
    try:
        mail = imaplib.IMAP4_SSL(IMAP_HOST)
        mail.login(IMAP_USER, IMAP_PASSWORD)
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

                    to_header = str(msg.get("To", ""))
                    match = re.search(r"\+([a-f0-9\-]+)@", to_header)

                    if not match:
                        subject, encoding = decode_header(msg.get("Subject", ""))[0]
                        if isinstance(subject, bytes):
                            subject = subject.decode(encoding if encoding else "utf-8")
                        match = re.search(r"\[REF:([a-f0-9\-]+)\]", subject)

                    if match:
                        log_id = match.group(1)
                        raw_body = extract_body(msg)
                        clean_body = clean_email_body(raw_body)

                        current_log_res = supabase.table("email_logs").select("response_text").eq("id", log_id).execute()

                        if current_log_res.data:
                            existing_history = current_log_res.data[0].get("response_text") or ""

                            if existing_history:
                                combined_response = f"{clean_body}\n\n━━━━━━━━━━━━━━━━━━━━\n\n{existing_history}"
                            else:
                                combined_response = clean_body

                            supabase.table("email_logs").update({
                                "response_text": combined_response[:10000]
                            }).eq("id", log_id).execute()

        mail.logout()
    except Exception as e:
        print(f"Background IMAP Sync Error: {e}")

async def email_sync_loop():
    while True:
        await asyncio.to_thread(sync_imap_emails)
        await asyncio.sleep(30)

@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(email_sync_loop())
    yield
    task.cancel()

app = FastAPI(title="Internal Email System API", lifespan=lifespan)

origins = [
    "http://localhost:3000",
    "http://localhost:5173",
    "https://superwiseemails.site",
    "https://www.superwiseemails.site",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Authentication Endpoints ---
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


# --- Email Endpoints ---
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
        "sender_email": FROM_EMAIL,
        "receiver_email": RECEIVER_EMAIL,
        "title": payload.title,
        "comments": payload.comments
    }
    result = supabase.table("email_logs").insert(log_data).execute()
    log_id = result.data[0]["id"]

    background_tasks.add_task(
        dispatch_actual_email,
        sender=FROM_EMAIL,
        receiver=RECEIVER_EMAIL,
        subject=payload.title,
        body=payload.comments,
        log_id=log_id
    )
    return {"status": "success"}


# --- USER MANAGEMENT ENDPOINTS ---

@app.get("/api/admin/users")
async def get_all_users(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin": raise HTTPException(status_code=403, detail="Admins only.")
    res = supabase.table("profiles").select("id, name, email, role").order("name").execute()
    return res.data

@app.post("/api/admin/users")
async def create_new_user(payload: CreateUserRequest, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin": raise HTTPException(status_code=403, detail="Admins only.")
    if payload.role not in ["admin", "employee"]: raise HTTPException(status_code=400, detail="Invalid role")

    hashed_pw = get_password_hash(payload.password)
    try:
        supabase.table("profiles").insert({
            "name": payload.name, "email": payload.email, "password": hashed_pw, "role": payload.role
        }).execute()
        return {"message": "User created successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Email may already exist.")

@app.put("/api/admin/users/{user_id}")
async def edit_user(user_id: str, payload: EditUserRequest, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin": raise HTTPException(status_code=403, detail="Admins only.")

    update_data = {"name": payload.name, "email": payload.email, "role": payload.role}
    if payload.password:
        update_data["password"] = get_password_hash(payload.password)

    try:
        supabase.table("profiles").update(update_data).eq("id", user_id).execute()
        return {"message": "User updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail="Failed to update user. Email might be in use.")

@app.delete("/api/admin/users/{user_id}")
async def delete_user(user_id: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin": raise HTTPException(status_code=403, detail="Admins only.")
    if current_user["id"] == user_id: raise HTTPException(status_code=400, detail="You cannot delete your own admin account.")

    supabase.table("profiles").delete().eq("id", user_id).execute()
    return {"message": "User deleted successfully"}