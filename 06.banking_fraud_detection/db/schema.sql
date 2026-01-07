CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(64) UNIQUE NOT NULL,
    account_number VARCHAR(64),
    email VARCHAR(255),
    phone VARCHAR(20),
    registration_date DATE,
    account_status VARCHAR(20) DEFAULT 'active',
    risk_profile VARCHAR(20) DEFAULT 'low',  -- low, medium, high
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS transactions (
    id SERIAL PRIMARY KEY,
    transaction_id VARCHAR(64) UNIQUE NOT NULL,
    user_id VARCHAR(64) REFERENCES users(user_id),
    amount DECIMAL(15, 2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    merchant VARCHAR(255),
    merchant_category VARCHAR(50),
    location VARCHAR(255),
    latitude REAL,
    longitude REAL,
    device_id VARCHAR(64),
    ip_address VARCHAR(45),
    transaction_type VARCHAR(50),  -- purchase, withdrawal, transfer, deposit
    payment_method VARCHAR(50),  -- card, bank_transfer, digital_wallet
    timestamp TIMESTAMP NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',  -- pending, approved, declined, flagged
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS user_profiles (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(64) REFERENCES users(user_id),
    avg_transaction_amount DECIMAL(15, 2),
    typical_merchants TEXT[],  -- Array of typical merchant categories
    typical_locations TEXT[],  -- Array of typical locations
    typical_transaction_times TIME[],  -- Typical times of day
    spending_pattern JSONB,  -- JSON with spending patterns
    device_fingerprints TEXT[],  -- Known device IDs
    last_updated TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS fraud_patterns (
    id SERIAL PRIMARY KEY,
    pattern_name VARCHAR(100) NOT NULL,
    pattern_type VARCHAR(50),  -- card_fraud, account_takeover, money_laundering, etc.
    description TEXT,
    detection_rules JSONB,  -- JSON with detection rules
    ml_model_path VARCHAR(255),  -- Path to ML model if applicable
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS risk_assessments (
    id SERIAL PRIMARY KEY,
    transaction_id VARCHAR(64) REFERENCES transactions(transaction_id),
    risk_score REAL NOT NULL CHECK (risk_score BETWEEN 0 AND 100),
    risk_level VARCHAR(20) NOT NULL,  -- low, medium, high, critical
    risk_factors JSONB,  -- JSON with risk factors and scores
    agent_analysis TEXT,  -- LLM-generated analysis
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS fraud_alerts (
    id SERIAL PRIMARY KEY,
    alert_id VARCHAR(64) UNIQUE NOT NULL,
    transaction_id VARCHAR(64) REFERENCES transactions(transaction_id),
    user_id VARCHAR(64) REFERENCES users(user_id),
    alert_type VARCHAR(50),  -- card_fraud, account_takeover, suspicious_activity, etc.
    severity VARCHAR(20) NOT NULL,  -- low, medium, high, critical
    risk_score REAL NOT NULL,
    status VARCHAR(20) DEFAULT 'open',  -- open, investigating, resolved, false_positive
    description TEXT,
    investigation_notes TEXT,
    resolved_by VARCHAR(100),
    resolved_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS agent_executions (
    id SERIAL PRIMARY KEY,
    transaction_id VARCHAR(64) REFERENCES transactions(transaction_id),
    agent_type VARCHAR(50) NOT NULL,  -- monitor, pattern_detection, risk_assessment, investigation, alert
    execution_status VARCHAR(20) DEFAULT 'pending',  -- pending, running, completed, failed
    input_data JSONB,
    output_data JSONB,
    execution_time_ms INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS investigation_cases (
    id SERIAL PRIMARY KEY,
    case_id VARCHAR(64) UNIQUE NOT NULL,
    alert_id VARCHAR(64) REFERENCES fraud_alerts(alert_id),
    transaction_id VARCHAR(64) REFERENCES transactions(transaction_id),
    investigator VARCHAR(100),
    case_status VARCHAR(20) DEFAULT 'open',  -- open, investigating, closed
    findings TEXT,
    decision VARCHAR(50),  -- fraud, legitimate, suspicious, undetermined
    resolution_notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    closed_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_transactions_user ON transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_transactions_timestamp ON transactions(timestamp);
CREATE INDEX IF NOT EXISTS idx_transactions_status ON transactions(status);
CREATE INDEX IF NOT EXISTS idx_risk_assessments_transaction ON risk_assessments(transaction_id);
CREATE INDEX IF NOT EXISTS idx_fraud_alerts_transaction ON fraud_alerts(transaction_id);
CREATE INDEX IF NOT EXISTS idx_fraud_alerts_status ON fraud_alerts(status);
CREATE INDEX IF NOT EXISTS idx_fraud_alerts_severity ON fraud_alerts(severity);
CREATE INDEX IF NOT EXISTS idx_agent_executions_transaction ON agent_executions(transaction_id);

