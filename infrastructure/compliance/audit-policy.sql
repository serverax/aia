CREATE TABLE IF NOT EXISTS compliance_audit_log (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    agent_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    decision TEXT NOT NULL,
    reason TEXT NOT NULL,
    source TEXT NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    previous_hash TEXT,
    audit_hash TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS compliance_audit_agent_idx
    ON compliance_audit_log (agent_id, timestamp DESC);

CREATE INDEX IF NOT EXISTS compliance_audit_event_idx
    ON compliance_audit_log (event_type, timestamp DESC);
