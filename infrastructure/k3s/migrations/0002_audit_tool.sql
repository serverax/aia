-- Sprint 6 migration: allow direction='tool' in audit_log so the tool sandbox
-- can write one row per tool invocation. Apply once before deploying the
-- Sprint 6 agent images.
--
--   psql -h <host> -U synthetic -d synthetic -f 0002_audit_tool.sql
-- or, in-cluster:
--   kubectl exec -n synthetic-enterprise postgres-0 -- \
--     psql -U synthetic -d synthetic -f /docker-entrypoint-initdb.d/migrations/0002.sql
--
-- Idempotent: safe to re-run.

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE table_name = 'audit_log' AND constraint_name = 'audit_log_direction_check'
    ) THEN
        ALTER TABLE audit_log DROP CONSTRAINT audit_log_direction_check;
    END IF;
END $$;

ALTER TABLE audit_log
    ADD CONSTRAINT audit_log_direction_check
    CHECK (direction IN ('in', 'out', 'tool'));
