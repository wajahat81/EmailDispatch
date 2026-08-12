-- =============================================================
-- Email Dispatch & Audit Platform — Database Schema
-- Run this in your Supabase SQL Editor or psql
-- =============================================================

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- -----------------------------------------------------------
-- 1. Profiles Table
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS profiles (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email      TEXT UNIQUE NOT NULL,
    password   TEXT NOT NULL,                       -- bcrypt hash
    role       TEXT NOT NULL CHECK (role IN ('admin', 'employee')),
    full_name  TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- -----------------------------------------------------------
-- 2. Email Logs Table
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS email_logs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sender_id       UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    sender_email    TEXT NOT NULL,
    receiver_email  TEXT NOT NULL,
    subject         TEXT NOT NULL,
    body            TEXT NOT NULL,
    sent_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Index for fast lookups by sender
CREATE INDEX IF NOT EXISTS idx_email_logs_sender_id ON email_logs(sender_id);
CREATE INDEX IF NOT EXISTS idx_email_logs_sent_at   ON email_logs(sent_at DESC);

-- -----------------------------------------------------------
-- 3. Seed Data (Default Test Users)
-- -----------------------------------------------------------
-- Passwords are bcrypt hashes of "admin123" and "employee123"
-- Generated with: passlib.hash.bcrypt.hash("admin123")

INSERT INTO profiles (id, email, password, role, full_name) VALUES
    (
        'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
        'admin@company.com',
        '$2b$12$TLBuz3Hnc.vJfVZOUA2UzuTsI.YYYOx5hcZIKD1Vq4O7194BBAgdG',
        'admin',
        'Admin User'
    ),
    (
        'b2c3d4e5-f6a7-8901-bcde-f12345678901',
        'employee@company.com',
        '$2b$12$mz4I98MwoOTMpRR7VGyveexTxvlu/pGkIHxcdCd.BiGFb7DOy9D.O',
        'employee',
        'John Employee'
    )
ON CONFLICT (email) DO NOTHING;
