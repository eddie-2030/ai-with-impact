# Research Report Writer - Multi-Agent Research & Analysis System

An enterprise-grade AI-powered system that uses multiple specialized agents to conduct research, analyze findings, verify sources, and generate comprehensive research reports with proper APA citations.

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

## Request a Research Report (Example)

```bash
curl -X POST http://localhost:8000/research \
  -H 'Content-Type: application/json' \
  -d '{
    "research_query": "What is the impact of AI on healthcare costs?",
    "research_type": "comprehensive",
    "max_sources": 20
  }'
```

## Features

- **Multi-Agent Architecture**: Specialized agents for research, analysis, fact-checking, and synthesis
- **Source Attribution**: All findings linked to sources with full metadata
- **Source Verification**: Fact-checking agent validates source credibility
- **APA Citations**: Proper APA 7th edition citations with reference list
- **Parallel Processing**: Agents work in parallel for efficiency
- **Quality Control**: Only verified sources above credibility threshold are used
- **Comprehensive Reports**: Structured reports with executive summary, findings, analysis, and references

## Agent Architecture

- **Research Agent**: Gathers information from web, academic databases, and internal sources
- **Analysis Agent**: Analyzes findings, identifies patterns, generates insights
- **Fact-Checking Agent**: Verifies source credibility and cross-references claims
- **Synthesis Agent**: Combines findings into coherent report with APA citations
- **Orchestrator**: Coordinates agents, manages workflow, ensures quality

## Notes

- Requires OpenAI API key for LLM functionality
- Web search tools require API keys (SerpAPI, Tavily) - see .env.example
- Database storage enables historical research tracking
- Supports both real-time and batch research requests

