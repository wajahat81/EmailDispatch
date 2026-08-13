import os
import resend
import jwt
import imaplib
import email
import random
import secrets
from email.header import decode_header
import re
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Header, Depends, BackgroundTasks
from pydantic import BaseModel
from supabase import create_client, Client
from passlib.context import CryptContext
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Request
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded


load_dotenv()

# --- 1. Structured Logging Setup ---
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# --- 2. Zero-Fallback Secrets Management ---
def get_env_or_fail(var_name: str) -> str:
    value = os.getenv(var_name)
    if not value:
        raise RuntimeError(f"CRITICAL ERROR: {var_name} environment variable is not set. Halting server.")
    return value

# Enforce strict existence of all critical variables
SUPABASE_URL = get_env_or_fail("SUPABASE_URL")
SUPABASE_KEY = get_env_or_fail("SUPABASE_KEY")
JWT_SECRET = get_env_or_fail("JWT_SECRET")
RESEND_API_KEY = get_env_or_fail("RESEND_API_KEY")
FROM_EMAIL = get_env_or_fail("FROM_EMAIL")
RECEIVER_EMAIL = get_env_or_fail("RECEIVER_EMAIL")

resend.api_key = RESEND_API_KEY
OTP_FROM_EMAIL = os.getenv("OTP_FROM_EMAIL", FROM_EMAIL) 

IMAP_HOST = os.getenv("IMAP_HOST", "imap.gmail.com") 
IMAP_USER = os.getenv("IMAP_USER")
IMAP_PASSWORD = os.getenv("IMAP_PASSWORD")

OTP_EXPIRY_MINUTES = 10

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# (Pydantic Models remain the same below this...)
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
    password: Optional[str] = None

class ForgotPasswordRequest(BaseModel):
    email: str

class ResetPasswordRequest(BaseModel):
    email: str
    otp: str
    new_password: str

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

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

def generate_otp() -> str:
    return f"{secrets.randbelow(1000000):06d}"

def send_otp_email(to_email: str, otp: str):
    try:
        resend.Emails.send({
            "from": OTP_FROM_EMAIL,
            "to": [to_email],
            "subject": "Your password reset code",
            "html": f"""
                <div style="font-family: sans-serif; max-width: 480px; margin: auto;">
                    <h2>Password Reset Request</h2>
                    <p>Use the code below to reset your password. This code expires in {OTP_EXPIRY_MINUTES} minutes.</p>
                    <div style="font-size: 32px; font-weight: bold; letter-spacing: 8px; background: #f1f5f9; padding: 16px; text-align: center; border-radius: 12px; margin: 20px 0;">
                        {otp}
                    </div>
                    <p style="color: #64748b; font-size: 13px;">If you didn't request this, you can safely ignore this email.</p>
                </div>
            """,
        })
        return True
    except Exception as e:
        print(f"Failed to send OTP email: {e}")
        return False

def dispatch_actual_email(sender: str, receiver: str, subject: str, body: str, log_id: str):
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


# --- Automated Background Sync Logic (Gmail IMAP) ---
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

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

raw_origins = os.getenv("ALLOWED_ORIGINS")
if raw_origins:
    origins = [origin.strip() for origin in raw_origins.split(",")]
else:
    # Absolute strict fallback to prevent local dev ports from accessing production
    origins = ["https://superwiseemails.site", "https://www.superwiseemails.site"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Authentication Endpoints ---
@app.post("/api/login")
@limiter.limit("5/minute")
async def login(request: Request, credentials: LoginRequest):
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


@app.post("/api/forgot-password")
@limiter.limit("3/minute") # Prevent email spamming
async def forgot_password(request: Request, payload: ForgotPasswordRequest, background_tasks: BackgroundTasks):
    # Always return the same generic response, whether or not the email exists —
    # this prevents attackers from using this endpoint to discover valid accounts.
    generic_response = {"message": "If an account with that email exists, a reset code has been sent."}

    user_res = supabase.table("profiles").select("id, email").eq("email", payload.email).execute()
    if not user_res.data:
        return generic_response

    otp = generate_otp()
    otp_hash = get_password_hash(otp)
    expires_at = (datetime.utcnow() + timedelta(minutes=OTP_EXPIRY_MINUTES)).isoformat()

    supabase.table("password_resets").insert({
        "email": payload.email,
        "otp_hash": otp_hash,
        "expires_at": expires_at,
        "used": False
    }).execute()

    background_tasks.add_task(send_otp_email, payload.email, otp)

    return generic_response


@app.post("/api/reset-password")
async def reset_password(payload: ResetPasswordRequest):
    # Get the most recent, unused OTP for this email
    res = supabase.table("password_resets") \
        .select("*") \
        .eq("email", payload.email) \
        .eq("used", False) \
        .order("created_at", desc=True) \
        .limit(1) \
        .execute()

    if not res.data:
        raise HTTPException(status_code=400, detail="Invalid or expired code")

    record = res.data[0]

    expires_at = datetime.fromisoformat(record["expires_at"])
    if datetime.utcnow() > expires_at.replace(tzinfo=None):
        raise HTTPException(status_code=400, detail="Code has expired. Please request a new one.")

    if not pwd_context.verify(payload.otp, record["otp_hash"]):
        raise HTTPException(status_code=400, detail="Invalid code")

    # Mark OTP as used
    supabase.table("password_resets").update({"used": True}).eq("id", record["id"]).execute()

    # Update the user's password
    new_hash = get_password_hash(payload.new_password)
    supabase.table("profiles").update({"password": new_hash}).eq("email", payload.email).execute()

    return {"message": "Password reset successfully"}


@app.put("/api/change-password")
async def change_password(payload: ChangePasswordRequest, current_user: dict = Depends(get_current_user)):
    user_res = supabase.table("profiles").select("*").eq("id", current_user["id"]).execute()
    if not user_res.data:
        raise HTTPException(status_code=404, detail="User not found")

    user = user_res.data[0]

    if not verify_password(payload.current_password, user["password"]):
        raise HTTPException(status_code=401, detail="Current password is incorrect")

    new_hash = get_password_hash(payload.new_password)
    supabase.table("profiles").update({"password": new_hash}).eq("id", current_user["id"]).execute()

    return {"message": "Password changed successfully"}


# --- Email Endpoints ---
@app.get("/api/emails")
async def get_emails(
    limit: int = 20, 
    offset: int = 0, 
    user: dict = Depends(get_current_user)
):
    query = supabase.table("email_logs").select("*, profiles!inner(name, email)")
    if user["role"] == "employee":
        query = query.eq("user_id", user["id"])
    
    # Apply pagination and sorting
    response = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
    
    formatted_data = []
    for log in response.data:
        log["sender_name"] = log["profiles"]["name"]
        log["sender_original_email"] = log["profiles"]["email"]
        formatted_data.append(log)
    return formatted_data

@app.post("/api/emails/send")
@limiter.limit("10/minute") 
async def send_email(
    request: Request,
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