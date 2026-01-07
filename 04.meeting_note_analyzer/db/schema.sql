CREATE TABLE IF NOT EXISTS meetings (
    id SERIAL PRIMARY KEY,
    meeting_ext_id VARCHAR(64) UNIQUE,
    title TEXT,
    date TIMESTAMP,
    participants TEXT[], -- Array of participant names
    transcript TEXT,
    summary TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS action_items (
    id SERIAL PRIMARY KEY,
    meeting_id INTEGER REFERENCES meetings(id) ON DELETE CASCADE,
    description TEXT NOT NULL,
    assignee TEXT,
    due_date DATE,
    status VARCHAR(32) DEFAULT 'open', -- open, in_progress, completed, cancelled
    priority VARCHAR(16) DEFAULT 'medium', -- low, medium, high
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS decisions (
    id SERIAL PRIMARY KEY,
    meeting_id INTEGER REFERENCES meetings(id) ON DELETE CASCADE,
    decision_text TEXT NOT NULL,
    rationale TEXT,
    decision_maker TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS topics (
    id SERIAL PRIMARY KEY,
    meeting_id INTEGER REFERENCES meetings(id) ON DELETE CASCADE,
    topic_text TEXT NOT NULL,
    relevance_score REAL, -- 0.0 to 1.0
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS participant_contributions (
    id SERIAL PRIMARY KEY,
    meeting_id INTEGER REFERENCES meetings(id) ON DELETE CASCADE,
    participant_name TEXT NOT NULL,
    contribution_count INTEGER DEFAULT 0,
    word_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_action_items_meeting ON action_items(meeting_id);
CREATE INDEX IF NOT EXISTS idx_decisions_meeting ON decisions(meeting_id);
CREATE INDEX IF NOT EXISTS idx_topics_meeting ON topics(meeting_id);
CREATE INDEX IF NOT EXISTS idx_meetings_date ON meetings(date);


