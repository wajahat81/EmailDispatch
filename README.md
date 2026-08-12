# Email Dispatch & Audit Platform

A full-stack email dispatch and audit logging system built with **React**, **FastAPI**, **Supabase (PostgreSQL)**, and **Tailwind CSS**.

---

## Quick Start

### 1. Database Setup

Run `schema.sql` in your Supabase SQL Editor (or any PostgreSQL instance):

```sql
-- Copy contents of schema.sql and run in Supabase SQL Editor
```

### 2. Backend Setup

```bash
cd backend
pip install -r requirements.txt

# Copy and configure environment variables
cp .env.example .env
# Edit .env with your actual values
```

**Environment Variables** (`.env`):

| Variable         | Description                           | Example                          |
|-----------------|---------------------------------------|----------------------------------|
| `DATABASE_URL`  | PostgreSQL connection string           | `postgresql://user:pass@host:5432/db` |
| `JWT_SECRET`    | Secret key for JWT signing            | `your-secret-key`                |
| `SENDER_EMAIL`  | Fixed outbound sender email           | `dispatch@company.com`           |
| `RECEIVER_EMAIL`| Fixed destination email               | `receiver@company.com`           |
| `SMTP_HOST`     | SMTP server hostname                  | `smtp.gmail.com`                 |
| `SMTP_PORT`     | SMTP server port                      | `587`                            |
| `SMTP_USER`     | SMTP auth username                    | `your-email@gmail.com`           |
| `SMTP_PASSWORD` | SMTP auth password (app password)     | `abcd-efgh-ijkl-mnop`           |

Start the backend:
```bash
uvicorn main:app --reload --port 8000
```

### 3. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The app will be available at `http://localhost:5173`.

---

## Default Test Accounts

After running `schema.sql`, you can log in with:

| Role     | Email                  | Password       |
|----------|------------------------|----------------|
| Admin    | `admin@company.com`    | `admin123`     |
| Employee | `employee@company.com` | `employee123`  |

> **Note**: The seed passwords in `schema.sql` must match. Run the password hash generation script below if you need to change them.

---

## Architecture

```
EmailDispatch/
├── backend/           # FastAPI REST API
│   ├── main.py        # App entry point
│   ├── config.py      # Environment config
│   ├── database.py    # PostgreSQL connection pool
│   ├── schemas.py     # Pydantic models
│   ├── auth.py        # JWT utilities
│   └── routers/       # API route handlers
├── frontend/          # React + Vite + Tailwind CSS
│   └── src/
│       ├── pages/     # LoginPage, Dashboard
│       ├── components/# Header, EmailModal, EmailDrawer
│       └── lib/       # API client, Auth context
└── schema.sql         # Database migration
```

## SMTP Note

If SMTP credentials are not configured, the system will still log emails to the database — it just won't actually send them. This allows development without an SMTP provider.
