"""
Pydantic models for request / response validation.
"""

from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from uuid import UUID


# ── Auth ──────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: str
    password: str


class UserInfo(BaseModel):
    id: str
    email: str
    role: str
    full_name: str


class LoginResponse(BaseModel):
    access_token: str
    user: UserInfo


# ── Email ─────────────────────────────────────────────────

class SendEmailRequest(BaseModel):
    subject: str
    body: str


class EmailLogOut(BaseModel):
    id: str
    sender_id: str
    sender_email: str
    receiver_email: str
    subject: str
    body: str
    sent_at: str
    sender_name: Optional[str] = None
    sender_user_email: Optional[str] = None


class SendEmailResponse(BaseModel):
    status: str
    message: str
    log: EmailLogOut
