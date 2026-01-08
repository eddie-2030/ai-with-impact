CREATE TABLE IF NOT EXISTS code_reviews (
    id SERIAL PRIMARY KEY,
    review_id VARCHAR(64) UNIQUE NOT NULL,
    code_content TEXT NOT NULL,
    language VARCHAR(50) NOT NULL,  -- python, sql, javascript, etc.
    file_path VARCHAR(255),
    status VARCHAR(20) DEFAULT 'pending',  -- pending, analyzing, completed, failed
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS security_findings (
    id SERIAL PRIMARY KEY,
    review_id INTEGER REFERENCES code_reviews(id) ON DELETE CASCADE,
    finding_type VARCHAR(50) NOT NULL,  -- sql_injection, xss, hardcoded_secret, etc.
    severity VARCHAR(20) NOT NULL,  -- critical, high, medium, low
    cwe_id VARCHAR(20),  -- CWE-79, CWE-89, etc.
    owasp_category VARCHAR(50),  -- A01, A02, etc.
    description TEXT NOT NULL,
    line_number INTEGER,
    code_snippet TEXT,
    confidence_score REAL CHECK (confidence_score BETWEEN 0 AND 100),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS performance_findings (
    id SERIAL PRIMARY KEY,
    review_id INTEGER REFERENCES code_reviews(id) ON DELETE CASCADE,
    finding_type VARCHAR(50) NOT NULL,  -- n_plus_one, slow_algorithm, missing_index, etc.
    severity VARCHAR(20) NOT NULL,  -- critical, high, medium, low
    description TEXT NOT NULL,
    line_number INTEGER,
    code_snippet TEXT,
    current_complexity VARCHAR(20),  -- O(n), O(n²), etc.
    suggested_complexity VARCHAR(20),
    confidence_score REAL CHECK (confidence_score BETWEEN 0 AND 100),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS quality_findings (
    id SERIAL PRIMARY KEY,
    review_id INTEGER REFERENCES code_reviews(id) ON DELETE CASCADE,
    finding_type VARCHAR(50) NOT NULL,  -- code_duplication, long_function, poor_naming, etc.
    severity VARCHAR(20) NOT NULL,  -- critical, high, medium, low
    description TEXT NOT NULL,
    line_number INTEGER,
    code_snippet TEXT,
    metric_value REAL,  -- cyclomatic complexity, function length, etc.
    confidence_score REAL CHECK (confidence_score BETWEEN 0 AND 100),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS code_rewrites (
    id SERIAL PRIMARY KEY,
    review_id INTEGER REFERENCES code_reviews(id) ON DELETE CASCADE,
    finding_id INTEGER,  -- References security_findings, performance_findings, or quality_findings
    finding_type VARCHAR(50),  -- security, performance, quality
    original_code TEXT NOT NULL,
    rewritten_code TEXT NOT NULL,
    explanation TEXT,
    confidence_score REAL CHECK (confidence_score BETWEEN 0 AND 100),
    rewrite_mode VARCHAR(20) DEFAULT 'suggest',  -- auto_apply, suggest, review
    applied BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS review_summaries (
    id SERIAL PRIMARY KEY,
    review_id INTEGER REFERENCES code_reviews(id) ON DELETE CASCADE,
    security_score REAL CHECK (security_score BETWEEN 0 AND 100),
    performance_score REAL CHECK (performance_score BETWEEN 0 AND 100),
    quality_score REAL CHECK (quality_score BETWEEN 0 AND 100),
    overall_score REAL CHECK (overall_score BETWEEN 0 AND 100),
    total_findings INTEGER DEFAULT 0,
    critical_findings INTEGER DEFAULT 0,
    high_findings INTEGER DEFAULT 0,
    medium_findings INTEGER DEFAULT 0,
    low_findings INTEGER DEFAULT 0,
    summary_text TEXT,
    recommendations TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS agent_executions (
    id SERIAL PRIMARY KEY,
    review_id INTEGER REFERENCES code_reviews(id) ON DELETE CASCADE,
    agent_type VARCHAR(50) NOT NULL,  -- analyzer, security, quality, performance, rewriter, coordinator
    execution_status VARCHAR(20) DEFAULT 'pending',  -- pending, running, completed, failed
    input_data JSONB,
    output_data JSONB,
    execution_time_ms INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_reviews_id ON code_reviews(review_id);
CREATE INDEX IF NOT EXISTS idx_reviews_status ON code_reviews(status);
CREATE INDEX IF NOT EXISTS idx_security_review ON security_findings(review_id);
CREATE INDEX IF NOT EXISTS idx_performance_review ON performance_findings(review_id);
CREATE INDEX IF NOT EXISTS idx_quality_review ON quality_findings(review_id);
CREATE INDEX IF NOT EXISTS idx_rewrites_review ON code_rewrites(review_id);
CREATE INDEX IF NOT EXISTS idx_summaries_review ON review_summaries(review_id);

