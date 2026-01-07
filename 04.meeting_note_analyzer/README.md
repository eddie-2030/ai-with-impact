# Meeting Notes Analyzer – LLM-Powered Action Item Extraction

This repo processes meeting transcripts/notes, extracts action items, decisions, key topics, and generates summaries using LLMs. It stores results in Postgres, exposes a FastAPI analysis endpoint, and visualizes insights in Streamlit.

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

## Analyze a Meeting (Example)

```bash
curl -X POST http://localhost:8000/analyze \
  -H 'Content-Type: application/json' \
  -d '{
    "meeting_id": "meeting-001",
    "title": "Q4 Planning Meeting",
    "date": "2025-01-15T10:00:00",
    "participants": ["John Doe", "Jane Smith"],
    "transcript": "John: We need to finalize the Q4 roadmap. Jane: I will create a draft by Friday. John: Great, and we should review the budget. Jane: I will schedule a follow-up meeting next week."
  }'
```

## Batch Processing

Drop JSON files like `data/meetings/meeting-*.json`:

```json
{
  "meeting_id": "meeting-002",
  "title": "Sprint Planning",
  "date": "2025-01-16T14:00:00",
  "participants": ["Alice", "Bob", "Charlie"],
  "transcript": "..."
}
```

Then run:

```bash
python -m pipeline.process_meetings
```

## Features

- **Action Item Extraction**: Automatically identifies action items with assignees and due dates
- **Decision Tracking**: Extracts key decisions made during meetings
- **Topic Extraction**: Identifies main topics and themes discussed
- **Summary Generation**: Creates concise meeting summaries
- **Participant Analysis**: Tracks who said what and participation levels
- **Follow-up Detection**: Identifies items requiring follow-up meetings

## Notes

- Requires OpenAI API key for LLM functionality
- Transcripts can be provided directly or processed from audio files (future enhancement)
- Supports both real-time analysis and batch processing
- Database storage enables historical analysis and trend tracking


