CREATE TABLE IF NOT EXISTS sc_rl_model_aware_research_records (
    record_id TEXT PRIMARY KEY, record JSONB NOT NULL, record_hash TEXT NOT NULL,
    created_utc TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS sc_rl_cross_product_exchanges (
    exchange_id TEXT PRIMARY KEY, record_id TEXT NOT NULL, record JSONB NOT NULL, record_hash TEXT NOT NULL,
    created_utc TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_sc_rl_cross_product_exchanges_record ON sc_rl_cross_product_exchanges(record_id);
CREATE TABLE IF NOT EXISTS sc_rl_cross_product_exchange_receipts (
    receipt_id TEXT PRIMARY KEY, exchange_id TEXT NOT NULL, record_id TEXT NOT NULL,
    record JSONB NOT NULL, record_hash TEXT NOT NULL, created_utc TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_sc_rl_cross_product_receipts_exchange ON sc_rl_cross_product_exchange_receipts(exchange_id);
CREATE TABLE IF NOT EXISTS sc_rl_model_aware_research_snapshots (
    snapshot_id TEXT PRIMARY KEY, record_id TEXT NOT NULL, snapshot_hash TEXT NOT NULL, record JSONB NOT NULL,
    created_utc TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS sc_rl_model_aware_research_events (
    event_id BIGSERIAL PRIMARY KEY, record_id TEXT NOT NULL, event_type TEXT NOT NULL, actor_ref TEXT NOT NULL,
    payload JSONB NOT NULL, event_hash TEXT NOT NULL, created_utc TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_sc_rl_model_aware_events_record ON sc_rl_model_aware_research_events(record_id, created_utc);
