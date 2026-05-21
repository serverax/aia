-- Audit log: every message every agent processes.
-- Same DDL is shipped into both docker-compose and K3s init.
-- Mounted at /docker-entrypoint-initdb.d/init.sql in the Postgres container
-- (only runs on a fresh data volume).

CREATE TABLE IF NOT EXISTS audit_log (
    id           BIGSERIAL PRIMARY KEY,
    timestamp    TIMESTAMPTZ NOT NULL,
    agent_id     TEXT        NOT NULL,
    message_id   TEXT        NOT NULL,
    task_id      TEXT        NOT NULL,
    direction    TEXT        NOT NULL CHECK (direction IN ('in', 'out')),
    message_type TEXT        NOT NULL,
    status       TEXT        NOT NULL,
    payload      JSONB       NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS audit_log_task_idx     ON audit_log (task_id);
CREATE INDEX IF NOT EXISTS audit_log_agent_idx    ON audit_log (agent_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS audit_log_msg_idx      ON audit_log (message_id);
