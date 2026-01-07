CREATE TABLE IF NOT EXISTS research_requests (
    id SERIAL PRIMARY KEY,
    request_id VARCHAR(64) UNIQUE,
    research_query TEXT NOT NULL,
    research_type VARCHAR(50) DEFAULT 'comprehensive',
    status VARCHAR(50) DEFAULT 'pending', -- pending, in_progress, completed, failed
    max_sources INTEGER DEFAULT 20,
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sources (
    id SERIAL PRIMARY KEY,
    source_id VARCHAR(64) UNIQUE,
    research_request_id INTEGER REFERENCES research_requests(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    authors TEXT[],  -- Array of author names
    publication_date DATE,
    url TEXT,
    doi TEXT,
    source_type VARCHAR(50),  -- academic_paper, news_article, report, website, book
    publisher TEXT,
    access_date DATE,  -- When we accessed the source
    credibility_score REAL DEFAULT 0.0,  -- 0.0 to 1.0 from fact-checking
    verification_status VARCHAR(20) DEFAULT 'pending',  -- pending, verified, questionable, unreliable
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS research_findings (
    id SERIAL PRIMARY KEY,
    research_request_id INTEGER REFERENCES research_requests(id) ON DELETE CASCADE,
    source_id INTEGER REFERENCES sources(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    quote TEXT,  -- Direct quote if applicable
    page_number VARCHAR(20),  -- For citations (e.g., "p. 15")
    in_text_citation TEXT,  -- Pre-formatted: (Author, Year)
    confidence_score REAL DEFAULT 0.5,
    agent_type VARCHAR(50),  -- research, analysis, fact_check
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS source_verifications (
    id SERIAL PRIMARY KEY,
    source_id INTEGER REFERENCES sources(id) ON DELETE CASCADE,
    url_valid BOOLEAN,
    domain_reputation TEXT,  -- high, medium, low
    author_verified BOOLEAN,
    peer_reviewed BOOLEAN,
    cross_reference_count INTEGER DEFAULT 0,
    consensus_level VARCHAR(20),  -- high, medium, low
    verification_details JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS research_reports (
    id SERIAL PRIMARY KEY,
    research_request_id INTEGER REFERENCES research_requests(id) ON DELETE CASCADE,
    report_content TEXT NOT NULL,  -- Full markdown report
    executive_summary TEXT,
    references_section TEXT,  -- APA formatted references
    word_count INTEGER,
    source_count INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS agent_executions (
    id SERIAL PRIMARY KEY,
    research_request_id INTEGER REFERENCES research_requests(id) ON DELETE CASCADE,
    agent_type VARCHAR(50) NOT NULL,  -- research, analysis, fact_check, synthesis, orchestrator
    execution_status VARCHAR(20) DEFAULT 'pending',  -- pending, running, completed, failed
    input_data JSONB,
    output_data JSONB,
    execution_time_seconds REAL,
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_sources_request ON sources(research_request_id);
CREATE INDEX IF NOT EXISTS idx_findings_request ON research_findings(research_request_id);
CREATE INDEX IF NOT EXISTS idx_findings_source ON research_findings(source_id);
CREATE INDEX IF NOT EXISTS idx_verifications_source ON source_verifications(source_id);
CREATE INDEX IF NOT EXISTS idx_reports_request ON research_reports(research_request_id);
CREATE INDEX IF NOT EXISTS idx_agent_executions_request ON agent_executions(research_request_id);


