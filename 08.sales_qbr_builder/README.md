# Sales/CS QBR Pack Builder – AI-Powered Quarterly Business Review Generator

This repo automatically generates comprehensive Quarterly Business Review (QBR) packs by aggregating data from CRM systems, product analytics, and support platforms. It uses LLMs to synthesize insights, identify wins/risks/opportunities, and create structured presentation decks with human-in-the-loop approval gates.

## License

This project is licensed under the MIT License - see the [LICENSE.txt](LICENSE.txt) file for details.

## Quick Start

### Prerequisites
- Python 3.8+
- OpenAI API Key
- PostgreSQL (optional, for persistent storage)
- Virtual environment (recommended)

### Installation

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env and add your OpenAI API key:
# OPENAI_API_KEY=sk-proj-your-key-here
```

### Run the Application

```bash
# Terminal 1: Start API server
export OPENAI_API_KEY=your-key-here
uvicorn api.server:app --reload --port 8000

# Terminal 2: Start Streamlit dashboard
export OPENAI_API_KEY=your-key-here
streamlit run dashboard/app.py
```

- API: http://localhost:8000/docs
- Dashboard: http://localhost:8501

## Generate a QBR Pack (Example)

```bash
curl -X POST http://localhost:8000/qbr/generate \
  -H 'Content-Type: application/json' \
  -d '{
    "account_id": "acc-001",
    "account_name": "Acme Corp",
    "quarter": "Q1-2025",
    "period_start": "2025-01-01",
    "period_end": "2025-03-31",
    "goals": ["Renewal", "Expansion", "Product Adoption"]
  }'
```

## Features

- **Automated Data Aggregation**: Pulls data from CRM, analytics, and support systems (via MCP servers)
- **AI-Powered Insights**: LLM generates wins, risks, and opportunities from aggregated data
- **Structured Output**: Generates consistent QBR outlines and slide decks
- **Human-in-the-Loop**: Approval gates ensure accuracy before final delivery
- **Export Capabilities**: Generates presentation-ready decks (PPTX, PDF)
- **Audit Trails**: Full traceability of data sources and AI reasoning

## Architecture

- **API Layer**: FastAPI REST API for QBR operations
- **Analysis Layer**: LLM-powered insight generation with schema-constrained outputs
- **Data Layer**: PostgreSQL database for QBR storage
- **MCP Integration**: MCP servers for CRM, Analytics, and Support data (read-only)
- **Dashboard**: Streamlit web interface for QBR generation and review

## Notes

- Requires OpenAI API key for LLM functionality
- MCP servers can be mocked for development (see `tools/` directory)
- Supports both real-time QBR generation and batch processing
- Database storage enables historical analysis and trend tracking
- Human-in-the-loop approval ensures quality and accuracy
