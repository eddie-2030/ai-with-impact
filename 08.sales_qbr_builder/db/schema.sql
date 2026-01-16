-- QBR Requests Table
CREATE TABLE IF NOT EXISTS qbr_requests (
    id SERIAL PRIMARY KEY,
    request_id VARCHAR(64) UNIQUE NOT NULL,
    account_id VARCHAR(64) NOT NULL,
    account_name TEXT,
    quarter VARCHAR(16),
    period_start DATE,
    period_end DATE,
    goals TEXT[], -- Array of goals/focus areas
    status VARCHAR(32) DEFAULT 'pending', -- pending, processing, completed, failed, approved, rejected
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- QBR Packs Table
CREATE TABLE IF NOT EXISTS qbr_packs (
    id SERIAL PRIMARY KEY,
    qbr_request_id INTEGER REFERENCES qbr_requests(id) ON DELETE CASCADE,
    pack_id VARCHAR(64) UNIQUE NOT NULL,
    executive_summary TEXT,
    account_health_score REAL, -- 0.0 to 1.0
    version INTEGER DEFAULT 1,
    status VARCHAR(32) DEFAULT 'draft', -- draft, pending_approval, approved, exported, rejected
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    approved_at TIMESTAMP,
    exported_at TIMESTAMP
);

-- Insights Table (Wins, Risks, Opportunities)
CREATE TABLE IF NOT EXISTS insights (
    id SERIAL PRIMARY KEY,
    qbr_pack_id INTEGER REFERENCES qbr_packs(id) ON DELETE CASCADE,
    insight_type VARCHAR(32) NOT NULL, -- win, risk, opportunity
    title TEXT NOT NULL,
    description TEXT,
    impact_score REAL, -- 0.0 to 1.0
    confidence_score REAL, -- 0.0 to 1.0
    category VARCHAR(64), -- usage, support, contract, product, etc.
    created_at TIMESTAMP DEFAULT NOW()
);

-- Data Sources Table (Aggregated data from CRM, Analytics, Support)
CREATE TABLE IF NOT EXISTS data_sources (
    id SERIAL PRIMARY KEY,
    qbr_pack_id INTEGER REFERENCES qbr_packs(id) ON DELETE CASCADE,
    source_type VARCHAR(32) NOT NULL, -- crm, analytics, support
    source_name VARCHAR(64), -- e.g., "Salesforce", "Mixpanel", "Zendesk"
    data_json JSONB, -- Flexible JSON storage for source-specific data
    fetched_at TIMESTAMP DEFAULT NOW(),
    data_quality_score REAL -- 0.0 to 1.0
);

-- Action Items Table
CREATE TABLE IF NOT EXISTS action_items (
    id SERIAL PRIMARY KEY,
    qbr_pack_id INTEGER REFERENCES qbr_packs(id) ON DELETE CASCADE,
    description TEXT NOT NULL,
    assignee TEXT,
    due_date DATE,
    priority VARCHAR(16) DEFAULT 'medium', -- low, medium, high
    status VARCHAR(32) DEFAULT 'open', -- open, in_progress, completed, cancelled
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

-- Approvals Table (Approval history and revisions)
CREATE TABLE IF NOT EXISTS approvals (
    id SERIAL PRIMARY KEY,
    qbr_pack_id INTEGER REFERENCES qbr_packs(id) ON DELETE CASCADE,
    approver_name TEXT,
    action VARCHAR(32) NOT NULL, -- approve, request_changes, reject
    feedback TEXT,
    revision_notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Metrics Table (Key metrics for QBR)
CREATE TABLE IF NOT EXISTS metrics (
    id SERIAL PRIMARY KEY,
    qbr_pack_id INTEGER REFERENCES qbr_packs(id) ON DELETE CASCADE,
    metric_name VARCHAR(64) NOT NULL,
    metric_value REAL,
    metric_unit VARCHAR(32),
    period_start DATE,
    period_end DATE,
    comparison_period_start DATE, -- For period-over-period comparison
    comparison_period_end DATE,
    comparison_value REAL,
    change_percent REAL,
    trend VARCHAR(16), -- up, down, stable
    created_at TIMESTAMP DEFAULT NOW()
);

-- Orchestrator runtime / audit log
CREATE TABLE IF NOT EXISTS qbr_runs (
    id SERIAL PRIMARY KEY,
    request_id VARCHAR(64),
    pack_id VARCHAR(64),
    status VARCHAR(32) DEFAULT 'running', -- running, completed, failed
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS qbr_events (
    id SERIAL PRIMARY KEY,
    qbr_run_id INTEGER,
    step VARCHAR(64),
    event_type VARCHAR(32), -- started, completed, error, checkpoint
    payload_json JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_qbr_requests_account ON qbr_requests(account_id);
CREATE INDEX IF NOT EXISTS idx_qbr_requests_status ON qbr_requests(status);
CREATE INDEX IF NOT EXISTS idx_qbr_packs_request ON qbr_packs(qbr_request_id);
CREATE INDEX IF NOT EXISTS idx_qbr_packs_status ON qbr_packs(status);
CREATE INDEX IF NOT EXISTS idx_insights_pack ON insights(qbr_pack_id);
CREATE INDEX IF NOT EXISTS idx_insights_type ON insights(insight_type);
CREATE INDEX IF NOT EXISTS idx_data_sources_pack ON data_sources(qbr_pack_id);
CREATE INDEX IF NOT EXISTS idx_data_sources_type ON data_sources(source_type);
CREATE INDEX IF NOT EXISTS idx_action_items_pack ON action_items(qbr_pack_id);
CREATE INDEX IF NOT EXISTS idx_approvals_pack ON approvals(qbr_pack_id);
CREATE INDEX IF NOT EXISTS idx_metrics_pack ON metrics(qbr_pack_id);
CREATE INDEX IF NOT EXISTS idx_qbr_runs_pack ON qbr_runs(pack_id);
CREATE INDEX IF NOT EXISTS idx_qbr_events_run ON qbr_events(qbr_run_id);
CREATE INDEX IF NOT EXISTS idx_qbr_events_step ON qbr_events(step);