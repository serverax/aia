-- ==========================================================
-- AIA Hiring Webapp DEV Supabase Schema
-- Schemas:
--   orchestrator_dev
--   rag_dev
--   semantic_dev
-- ==========================================================

create extension if not exists pgcrypto;
create extension if not exists vector;

create schema if not exists orchestrator_dev;
create schema if not exists rag_dev;
create schema if not exists semantic_dev;

create or replace function public.aia_set_updated_at()
returns trigger
language plpgsql
set search_path = public
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

-- ==========================================================
-- Orchestrator Service DB
-- ==========================================================

create table if not exists orchestrator_dev.jobs (
  id uuid primary key default gen_random_uuid(),
  type text not null,
  payload jsonb not null default '{}'::jsonb,
  status text not null default 'queued',
  priority int not null default 5,
  attempts int not null default 0,
  max_attempts int not null default 3,
  locked_by text,
  locked_at timestamptz,
  scheduled_at timestamptz not null default now(),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists orchestrator_dev.job_status (
  id uuid primary key default gen_random_uuid(),
  job_id uuid not null references orchestrator_dev.jobs(id) on delete cascade,
  status text not null,
  message text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists orchestrator_dev.agent_config (
  id uuid primary key default gen_random_uuid(),
  name text not null unique,
  type text not null,
  config jsonb not null default '{}'::jsonb,
  enabled boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists orchestrator_dev.agent_status (
  id uuid primary key default gen_random_uuid(),
  agent_id uuid not null references orchestrator_dev.agent_config(id) on delete cascade,
  status text not null,
  last_seen timestamptz,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_orch_dev_jobs_type on orchestrator_dev.jobs(type);
create index if not exists idx_orch_dev_jobs_status on orchestrator_dev.jobs(status);
create index if not exists idx_orch_dev_jobs_scheduled_at on orchestrator_dev.jobs(scheduled_at);
create index if not exists idx_orch_dev_job_status_job_id on orchestrator_dev.job_status(job_id);
create index if not exists idx_orch_dev_agent_status_agent_id on orchestrator_dev.agent_status(agent_id);

drop trigger if exists trg_orch_dev_jobs_updated_at on orchestrator_dev.jobs;
create trigger trg_orch_dev_jobs_updated_at
before update on orchestrator_dev.jobs
for each row execute function public.aia_set_updated_at();

drop trigger if exists trg_orch_dev_job_status_updated_at on orchestrator_dev.job_status;
create trigger trg_orch_dev_job_status_updated_at
before update on orchestrator_dev.job_status
for each row execute function public.aia_set_updated_at();

drop trigger if exists trg_orch_dev_agent_config_updated_at on orchestrator_dev.agent_config;
create trigger trg_orch_dev_agent_config_updated_at
before update on orchestrator_dev.agent_config
for each row execute function public.aia_set_updated_at();

drop trigger if exists trg_orch_dev_agent_status_updated_at on orchestrator_dev.agent_status;
create trigger trg_orch_dev_agent_status_updated_at
before update on orchestrator_dev.agent_status
for each row execute function public.aia_set_updated_at();

-- ==========================================================
-- RAG Service DB
-- ==========================================================

create table if not exists rag_dev.documents (
  id uuid primary key default gen_random_uuid(),
  source text not null,
  content text not null,
  metadata jsonb not null default '{}'::jsonb,
  content_hash text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists rag_dev.embeddings (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references rag_dev.documents(id) on delete cascade,
  embedding vector(1536),
  model text not null default 'text-embedding-3-small',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists rag_dev.queries (
  id uuid primary key default gen_random_uuid(),
  query text not null,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists rag_dev.results (
  id uuid primary key default gen_random_uuid(),
  query_id uuid not null references rag_dev.queries(id) on delete cascade,
  document_id uuid not null references rag_dev.documents(id) on delete cascade,
  score double precision not null,
  created_at timestamptz not null default now()
);

create index if not exists idx_rag_dev_documents_source on rag_dev.documents(source);
create index if not exists idx_rag_dev_documents_metadata on rag_dev.documents using gin(metadata);
create index if not exists idx_rag_dev_documents_hash on rag_dev.documents(content_hash);
create index if not exists idx_rag_dev_embeddings_document_id on rag_dev.embeddings(document_id);
create index if not exists idx_rag_dev_results_query_id on rag_dev.results(query_id);
create index if not exists idx_rag_dev_results_document_id on rag_dev.results(document_id);

-- Enable later when enough rows exist:
-- create index if not exists idx_rag_dev_embeddings_hnsw
--   on rag_dev.embeddings using hnsw (embedding vector_cosine_ops);

drop trigger if exists trg_rag_dev_documents_updated_at on rag_dev.documents;
create trigger trg_rag_dev_documents_updated_at
before update on rag_dev.documents
for each row execute function public.aia_set_updated_at();

drop trigger if exists trg_rag_dev_embeddings_updated_at on rag_dev.embeddings;
create trigger trg_rag_dev_embeddings_updated_at
before update on rag_dev.embeddings
for each row execute function public.aia_set_updated_at();

-- ==========================================================
-- Semantic Search Service DB
-- ==========================================================

create table if not exists semantic_dev.indexes (
  id uuid primary key default gen_random_uuid(),
  name text not null unique,
  description text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists semantic_dev.documents (
  id uuid primary key default gen_random_uuid(),
  index_id uuid references semantic_dev.indexes(id) on delete cascade,
  source text not null,
  content text not null,
  metadata jsonb not null default '{}'::jsonb,
  content_hash text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists semantic_dev.embeddings (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references semantic_dev.documents(id) on delete cascade,
  embedding vector(1536),
  model text not null default 'text-embedding-3-small',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_semantic_dev_indexes_name on semantic_dev.indexes(name);
create index if not exists idx_semantic_dev_documents_index_id on semantic_dev.documents(index_id);
create index if not exists idx_semantic_dev_documents_source on semantic_dev.documents(source);
create index if not exists idx_semantic_dev_documents_metadata on semantic_dev.documents using gin(metadata);
create index if not exists idx_semantic_dev_documents_hash on semantic_dev.documents(content_hash);
create index if not exists idx_semantic_dev_embeddings_document_id on semantic_dev.embeddings(document_id);

-- Enable later when enough rows exist:
-- create index if not exists idx_semantic_dev_embeddings_hnsw
--   on semantic_dev.embeddings using hnsw (embedding vector_cosine_ops);

drop trigger if exists trg_semantic_dev_indexes_updated_at on semantic_dev.indexes;
create trigger trg_semantic_dev_indexes_updated_at
before update on semantic_dev.indexes
for each row execute function public.aia_set_updated_at();

drop trigger if exists trg_semantic_dev_documents_updated_at on semantic_dev.documents;
create trigger trg_semantic_dev_documents_updated_at
before update on semantic_dev.documents
for each row execute function public.aia_set_updated_at();

drop trigger if exists trg_semantic_dev_embeddings_updated_at on semantic_dev.embeddings;
create trigger trg_semantic_dev_embeddings_updated_at
before update on semantic_dev.embeddings
for each row execute function public.aia_set_updated_at();

insert into semantic_dev.indexes(name, description, metadata)
values
  ('candidate-cv-dev-index', 'DEV index for candidate CVs', '{"env":"dev","type":"candidate"}'),
  ('job-description-dev-index', 'DEV index for job descriptions', '{"env":"dev","type":"job"}'),
  ('interview-qa-dev-index', 'DEV index for interview questions and answers', '{"env":"dev","type":"interview"}')
on conflict (name) do nothing;
