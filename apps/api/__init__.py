"""AIA / OrdinoxAI Hiring API.

A FastAPI service exposing CRUD + AI-scoring over the ``ordinoxai`` Postgres
schema (see ``supabase/migrations/001_ordinoxai_aia_core_schema.sql``). The
service is the backbone the web frontend and agent/worker services build on.
"""
