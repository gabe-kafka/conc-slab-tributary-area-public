CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS projects (
  id text PRIMARY KEY DEFAULT gen_random_uuid()::text,
  user_id text NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name text NOT NULL,
  dxf_blob_url text NOT NULL,
  dxf_filename text NOT NULL,
  dxf_size_bytes bigint,
  source_units text NOT NULL,
  layer_mapping jsonb NOT NULL,
  result jsonb NOT NULL,
  view_mode text NOT NULL DEFAULT 'plan',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS projects_user_id_idx ON projects (user_id, updated_at DESC);
