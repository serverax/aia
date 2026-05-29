CREATE SCHEMA IF NOT EXISTS ordinoxai;

-- Required for UUIDs
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- =========================================================
-- 1. Companies / Customers
-- =========================================================
CREATE TABLE IF NOT EXISTS ordinoxai.companies (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL,
  website text,
  industry text,
  country text,
  status text NOT NULL DEFAULT 'active',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

-- =========================================================
-- 2. Users / Platform Accounts
-- =========================================================
CREATE TABLE IF NOT EXISTS ordinoxai.users (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id uuid REFERENCES ordinoxai.companies(id) ON DELETE SET NULL,
  email text NOT NULL UNIQUE,
  full_name text,
  role text NOT NULL DEFAULT 'user',
  status text NOT NULL DEFAULT 'active',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

-- =========================================================
-- 3. Job Campaigns
-- =========================================================
CREATE TABLE IF NOT EXISTS ordinoxai.jobs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id uuid REFERENCES ordinoxai.companies(id) ON DELETE CASCADE,
  created_by uuid REFERENCES ordinoxai.users(id) ON DELETE SET NULL,

  title text NOT NULL,
  department text,
  location text,
  employment_type text,
  seniority text,

  description text NOT NULL,
  requirements text,
  salary_min numeric,
  salary_max numeric,
  currency text DEFAULT 'GBP',

  status text NOT NULL DEFAULT 'draft',

  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

-- =========================================================
-- 4. Candidates
-- =========================================================
CREATE TABLE IF NOT EXISTS ordinoxai.candidates (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),

  full_name text NOT NULL,
  email text,
  phone text,
  country text,
  linkedin_url text,
  portfolio_url text,

  source text,
  status text NOT NULL DEFAULT 'new',

  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),

  CONSTRAINT candidates_email_unique UNIQUE (email)
);

-- =========================================================
-- 5. Applications
-- =========================================================
CREATE TABLE IF NOT EXISTS ordinoxai.applications (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),

  job_id uuid NOT NULL REFERENCES ordinoxai.jobs(id) ON DELETE CASCADE,
  candidate_id uuid NOT NULL REFERENCES ordinoxai.candidates(id) ON DELETE CASCADE,

  status text NOT NULL DEFAULT 'submitted',
  stage text NOT NULL DEFAULT 'screening',

  cv_file_url text,
  cover_letter text,

  ai_score numeric,
  ai_summary text,
  ai_risk_flags jsonb NOT NULL DEFAULT '[]'::jsonb,
  ai_recommendation text,

  submitted_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),

  CONSTRAINT unique_candidate_job_application UNIQUE (job_id, candidate_id)
);

-- =========================================================
-- 6. Agent Config
-- =========================================================
CREATE TABLE IF NOT EXISTS ordinoxai.agent_config (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),

  name text NOT NULL,
  type text NOT NULL,
  description text,

  config jsonb NOT NULL DEFAULT '{}'::jsonb,
  enabled boolean NOT NULL DEFAULT true,

  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

-- =========================================================
-- 7. Agent Jobs / Tasks
-- =========================================================
CREATE TABLE IF NOT EXISTS ordinoxai.agent_jobs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),

  agent_id uuid REFERENCES ordinoxai.agent_config(id) ON DELETE SET NULL,
  job_id uuid REFERENCES ordinoxai.jobs(id) ON DELETE CASCADE,
  application_id uuid REFERENCES ordinoxai.applications(id) ON DELETE CASCADE,

  type text NOT NULL,
  payload jsonb NOT NULL DEFAULT '{}'::jsonb,

  status text NOT NULL DEFAULT 'queued',
  priority integer NOT NULL DEFAULT 5,

  started_at timestamptz,
  completed_at timestamptz,
  error_message text,

  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

-- =========================================================
-- 8. Agent Status / Runtime Heartbeat
-- =========================================================
CREATE TABLE IF NOT EXISTS ordinoxai.agent_status (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),

  agent_id uuid REFERENCES ordinoxai.agent_config(id) ON DELETE CASCADE,

  status text NOT NULL DEFAULT 'idle',
  current_task text,
  last_heartbeat_at timestamptz,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,

  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

-- =========================================================
-- 9. Interviews
-- =========================================================
CREATE TABLE IF NOT EXISTS ordinoxai.interviews (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),

  application_id uuid NOT NULL REFERENCES ordinoxai.applications(id) ON DELETE CASCADE,

  scheduled_at timestamptz,
  duration_minutes integer DEFAULT 60,
  location text,
  meeting_url text,

  interviewer_name text,
  interviewer_email text,

  status text NOT NULL DEFAULT 'scheduled',
  notes text,
  feedback jsonb NOT NULL DEFAULT '{}'::jsonb,

  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

-- =========================================================
-- 10. Audit Logs
-- =========================================================
CREATE TABLE IF NOT EXISTS ordinoxai.audit_logs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),

  actor_user_id uuid REFERENCES ordinoxai.users(id) ON DELETE SET NULL,
  entity_type text NOT NULL,
  entity_id uuid,
  action text NOT NULL,

  old_data jsonb,
  new_data jsonb,

  ip_address text,
  user_agent text,

  created_at timestamptz NOT NULL DEFAULT now()
);

-- =========================================================
-- 11. Waitlist / Public Leads
-- =========================================================
CREATE TABLE IF NOT EXISTS ordinoxai.waitlist_users (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),

  email text NOT NULL UNIQUE,
  full_name text,
  company_name text,
  country text,
  role text,
  notes text,

  status text NOT NULL DEFAULT 'new',

  ip_address text,
  user_agent text,

  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

-- =========================================================
-- 12. Updated At Trigger
-- =========================================================
CREATE OR REPLACE FUNCTION ordinoxai.set_updated_at()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = ordinoxai, public
AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;

-- Apply updated_at triggers
DROP TRIGGER IF EXISTS trg_companies_updated_at ON ordinoxai.companies;
CREATE TRIGGER trg_companies_updated_at
BEFORE UPDATE ON ordinoxai.companies
FOR EACH ROW EXECUTE FUNCTION ordinoxai.set_updated_at();

DROP TRIGGER IF EXISTS trg_users_updated_at ON ordinoxai.users;
CREATE TRIGGER trg_users_updated_at
BEFORE UPDATE ON ordinoxai.users
FOR EACH ROW EXECUTE FUNCTION ordinoxai.set_updated_at();

DROP TRIGGER IF EXISTS trg_jobs_updated_at ON ordinoxai.jobs;
CREATE TRIGGER trg_jobs_updated_at
BEFORE UPDATE ON ordinoxai.jobs
FOR EACH ROW EXECUTE FUNCTION ordinoxai.set_updated_at();

DROP TRIGGER IF EXISTS trg_candidates_updated_at ON ordinoxai.candidates;
CREATE TRIGGER trg_candidates_updated_at
BEFORE UPDATE ON ordinoxai.candidates
FOR EACH ROW EXECUTE FUNCTION ordinoxai.set_updated_at();

DROP TRIGGER IF EXISTS trg_applications_updated_at ON ordinoxai.applications;
CREATE TRIGGER trg_applications_updated_at
BEFORE UPDATE ON ordinoxai.applications
FOR EACH ROW EXECUTE FUNCTION ordinoxai.set_updated_at();

DROP TRIGGER IF EXISTS trg_agent_config_updated_at ON ordinoxai.agent_config;
CREATE TRIGGER trg_agent_config_updated_at
BEFORE UPDATE ON ordinoxai.agent_config
FOR EACH ROW EXECUTE FUNCTION ordinoxai.set_updated_at();

DROP TRIGGER IF EXISTS trg_agent_jobs_updated_at ON ordinoxai.agent_jobs;
CREATE TRIGGER trg_agent_jobs_updated_at
BEFORE UPDATE ON ordinoxai.agent_jobs
FOR EACH ROW EXECUTE FUNCTION ordinoxai.set_updated_at();

DROP TRIGGER IF EXISTS trg_agent_status_updated_at ON ordinoxai.agent_status;
CREATE TRIGGER trg_agent_status_updated_at
BEFORE UPDATE ON ordinoxai.agent_status
FOR EACH ROW EXECUTE FUNCTION ordinoxai.set_updated_at();

DROP TRIGGER IF EXISTS trg_interviews_updated_at ON ordinoxai.interviews;
CREATE TRIGGER trg_interviews_updated_at
BEFORE UPDATE ON ordinoxai.interviews
FOR EACH ROW EXECUTE FUNCTION ordinoxai.set_updated_at();

DROP TRIGGER IF EXISTS trg_waitlist_users_updated_at ON ordinoxai.waitlist_users;
CREATE TRIGGER trg_waitlist_users_updated_at
BEFORE UPDATE ON ordinoxai.waitlist_users
FOR EACH ROW EXECUTE FUNCTION ordinoxai.set_updated_at();

-- =========================================================
-- Indexes
-- =========================================================
CREATE INDEX IF NOT EXISTS idx_users_company_id
  ON ordinoxai.users(company_id);

CREATE INDEX IF NOT EXISTS idx_jobs_company_id
  ON ordinoxai.jobs(company_id);

CREATE INDEX IF NOT EXISTS idx_jobs_status
  ON ordinoxai.jobs(status);

CREATE INDEX IF NOT EXISTS idx_candidates_email
  ON ordinoxai.candidates(email);

CREATE INDEX IF NOT EXISTS idx_applications_job_id
  ON ordinoxai.applications(job_id);

CREATE INDEX IF NOT EXISTS idx_applications_candidate_id
  ON ordinoxai.applications(candidate_id);

CREATE INDEX IF NOT EXISTS idx_applications_status
  ON ordinoxai.applications(status);

CREATE INDEX IF NOT EXISTS idx_agent_jobs_status
  ON ordinoxai.agent_jobs(status);

CREATE INDEX IF NOT EXISTS idx_agent_jobs_type
  ON ordinoxai.agent_jobs(type);

CREATE INDEX IF NOT EXISTS idx_waitlist_users_email
  ON ordinoxai.waitlist_users(email);

CREATE INDEX IF NOT EXISTS idx_waitlist_users_country
  ON ordinoxai.waitlist_users(country);

CREATE INDEX IF NOT EXISTS idx_waitlist_users_status
  ON ordinoxai.waitlist_users(status);

CREATE INDEX IF NOT EXISTS idx_audit_logs_entity
  ON ordinoxai.audit_logs(entity_type, entity_id);

