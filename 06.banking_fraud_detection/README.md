# Banking Fraud Detection System - Multi-Agent AI Fraud Detection

An enterprise-grade AI-powered fraud detection system that uses multiple specialized agents to monitor transactions, detect fraud patterns, assess risk, and generate alerts in real-time.

## License

This project is licensed under the MIT License - see the [LICENSE.txt](LICENSE.txt) file for details.

## Quick Start

### Prerequisites
- Python 3.8+
- OpenAI API Key (for LLM-powered analysis)
- PostgreSQL (for transaction and fraud data storage)
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

## Process a Transaction (Example)

```bash
curl -X POST http://localhost:8000/transactions \
  -H 'Content-Type: application/json' \
  -d '{
    "transaction_id": "txn-001",
    "user_id": "user-123",
    "amount": 1500.00,
    "merchant": "Online Store",
    "location": "New York, NY",
    "timestamp": "2025-01-20T14:30:00",
    "device_id": "device-456",
    "transaction_type": "purchase"
  }'
```

## Features

- **Multi-Agent Architecture**: Specialized agents for monitoring, pattern detection, risk assessment, and investigation
- **Real-Time Processing**: Monitor and analyze transactions as they occur
- **Pattern Detection**: Identifies various fraud types (card fraud, account takeover, money laundering)
- **Risk Scoring**: Calculates composite risk scores (0-100) with severity classification
- **Behavioral Analysis**: User behavior profiling and anomaly detection
- **Alert Management**: Generates prioritized alerts with investigation workflows
- **Comprehensive Reporting**: Fraud analysis reports with explanations

## Agent Architecture

- **Transaction Monitor Agent**: Real-time transaction monitoring and feature extraction
- **Pattern Detection Agent**: Identifies fraud patterns and behavioral anomalies
- **Risk Assessment Agent**: Calculates risk scores and determines severity
- **Investigation Agent**: Performs deep analysis and gathers additional context
- **Alert Agent**: Generates and routes fraud alerts
- **Orchestrator**: Coordinates agents and manages workflow

## Notes

- Requires OpenAI API key for LLM-powered analysis
- Database storage enables historical fraud pattern analysis
- Supports both real-time and batch transaction processing
- Designed for high-throughput transaction processing

