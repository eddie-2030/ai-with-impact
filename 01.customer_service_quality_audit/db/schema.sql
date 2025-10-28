CREATE TABLE IF NOT EXISTS agents (
    id SERIAL PRIMARY KEY,
    agent_ext_id VARCHAR(64) UNIQUE,
    name TEXT
);

CREATE TABLE IF NOT EXISTS conversations (
    id SERIAL PRIMARY KEY,
    conv_ext_id VARCHAR(64) UNIQUE,
    agent_id INTEGER REFERENCES agents(id),
    started_at TIMESTAMP,
    channel VARCHAR(16), -- call, chat
    language VARCHAR(16),
    raw_text TEXT,
    redacted_text TEXT
);

CREATE TABLE IF NOT EXISTS scores (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER REFERENCES conversations(id) ON DELETE CASCADE,
    model_version TEXT,
    professionalism REAL CHECK (professionalism BETWEEN 0 AND 5),
    friendliness REAL CHECK (friendliness BETWEEN 0 AND 5),
    resolution_effectiveness REAL CHECK (resolution_effectiveness BETWEEN 0 AND 5),
    explanation JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS human_labels (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER REFERENCES conversations(id) ON DELETE CASCADE,
    professionalism INTEGER,
    friendliness INTEGER,
    resolution_effectiveness INTEGER,
    notes TEXT,
    labeled_by TEXT,
    labeled_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_scores_conv ON scores(conversation_id);
CREATE INDEX IF NOT EXISTS idx_hlabels_conv ON human_labels(conversation_id);
