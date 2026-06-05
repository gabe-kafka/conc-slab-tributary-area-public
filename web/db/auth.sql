CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS users (
  id text PRIMARY KEY DEFAULT gen_random_uuid()::text,
  name text,
  email text UNIQUE,
  "emailVerified" timestamptz,
  image text
);

CREATE TABLE IF NOT EXISTS accounts (
  id text PRIMARY KEY DEFAULT gen_random_uuid()::text,
  "userId" text NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  type text NOT NULL,
  provider text NOT NULL,
  "providerAccountId" text NOT NULL,
  refresh_token text,
  access_token text,
  expires_at bigint,
  token_type text,
  scope text,
  id_token text,
  session_state text,
  UNIQUE (provider, "providerAccountId")
);

CREATE INDEX IF NOT EXISTS accounts_user_id_idx ON accounts ("userId");

CREATE TABLE IF NOT EXISTS sessions (
  id text PRIMARY KEY DEFAULT gen_random_uuid()::text,
  "sessionToken" text UNIQUE NOT NULL,
  "userId" text NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  expires timestamptz NOT NULL
);

CREATE INDEX IF NOT EXISTS sessions_user_id_idx ON sessions ("userId");

CREATE TABLE IF NOT EXISTS verification_token (
  identifier text NOT NULL,
  token text NOT NULL,
  expires timestamptz NOT NULL,
  PRIMARY KEY (identifier, token)
);
