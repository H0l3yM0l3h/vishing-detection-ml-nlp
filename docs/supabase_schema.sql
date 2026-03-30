-- ============================================================
-- ShieldGuard — Supabase Schema
-- Run this entire file in your Supabase SQL Editor once.
-- ============================================================

-- 1. USERS
-- Stores account credentials and metadata.
CREATE TABLE IF NOT EXISTS users (
    id            BIGSERIAL    PRIMARY KEY,
    username      TEXT         UNIQUE NOT NULL,
    password_hash TEXT         NOT NULL,          -- bcrypt hash stored as text
    role          TEXT         DEFAULT 'user',
    created_at    TIMESTAMPTZ  DEFAULT now(),
    last_login    TIMESTAMPTZ
);

-- 2. LOGIN ATTEMPTS
-- Used for brute-force lockout (5 failures → 15 min lock).
CREATE TABLE IF NOT EXISTS login_attempts (
    id           BIGSERIAL   PRIMARY KEY,
    username     TEXT        NOT NULL,
    success      BOOLEAN     NOT NULL DEFAULT FALSE,
    attempted_at TIMESTAMPTZ DEFAULT now()
);

-- Index speeds up the lockout check query
CREATE INDEX IF NOT EXISTS idx_login_attempts_user_time
    ON login_attempts (username, attempted_at DESC);

-- 3. AUDIT LOG
-- Every scan is recorded — required for FYP evaluation.
CREATE TABLE IF NOT EXISTS audit_log (
    id           BIGSERIAL   PRIMARY KEY,
    username     TEXT        NOT NULL,
    input_length INTEGER,
    input_mode   TEXT,                            -- 'text' or 'audio'
    model_used   TEXT,
    verdict      TEXT,                            -- 'vishing' or 'safe'
    confidence   NUMERIC(6, 4),
    analyzed_at  TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_audit_log_user_time
    ON audit_log (username, analyzed_at DESC);

-- 4. RATE LIMIT
-- Tracks analysis counts per user per hour.
CREATE TABLE IF NOT EXISTS rate_limit (
    id          BIGSERIAL   PRIMARY KEY,
    username    TEXT        NOT NULL,
    action      TEXT        NOT NULL DEFAULT 'analyze',
    occurred_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_rate_limit_user_time
    ON rate_limit (username, occurred_at DESC);

-- ============================================================
-- ROW LEVEL SECURITY (RLS)
-- Prevents users from reading each other's data via the API.
-- ============================================================

ALTER TABLE users          ENABLE ROW LEVEL SECURITY;
ALTER TABLE login_attempts ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_log      ENABLE ROW LEVEL SECURITY;
ALTER TABLE rate_limit     ENABLE ROW LEVEL SECURITY;

-- Allow the service role (your backend) full access.
-- The anon key can only INSERT into login_attempts (for the attempt record).
-- All sensitive reads/writes happen server-side with the service role key.

-- If using service role key in secrets.toml, RLS won't block you.
-- If using anon key, add policies here for each table as needed.

-- Example policy (adjust to your auth setup):
-- CREATE POLICY "service_full_access" ON users
--     FOR ALL USING (true);

app/supabase_schema.sql