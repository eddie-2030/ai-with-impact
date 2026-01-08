# Code Security Reviewer - Multi-Agent Code Review & Auto-Rewrite System

An enterprise-grade AI-powered code review system that uses multiple specialized agents to analyze code for security vulnerabilities, performance issues, and quality problems, with automatic code rewriting capabilities.

## License

This project is licensed under the MIT License - see the [LICENSE.txt](LICENSE.txt) file for details.

## Quick Start

### Prerequisites
- Python 3.8+
- OpenAI API Key (for LLM-powered analysis and code rewriting)
- PostgreSQL (for storing code reviews and analysis results)
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

## Test with Example Code

The system includes test cases in `data/test_cases/`:
- **Python**: Secure vs Insecure, Efficient vs Inefficient examples
- **SQL**: Secure vs Insecure, Efficient vs Inefficient examples

Use the dashboard to test these examples and see the agents in action!

## Features

- **Multi-Agent Architecture**: Specialized agents for code analysis, security, quality, performance, and rewriting
- **Security Analysis**: Detects OWASP Top 10 vulnerabilities, CWE issues, and security anti-patterns
- **Performance Analysis**: Identifies inefficiencies, N+1 queries, algorithm issues, and optimization opportunities
- **Code Quality**: Checks maintainability, best practices, and code standards
- **Auto-Rewrite**: Automatically fixes code issues with confidence-based application
- **Test Cases**: Includes examples of secure/insecure and efficient/inefficient code

## Agent Architecture

- **Code Analyzer Agent**: Analyzes code structure and patterns
- **Security Agent**: Detects vulnerabilities and security issues
- **Quality Agent**: Checks code quality and best practices
- **Performance Agent**: Identifies performance bottlenecks
- **Code Rewriter Agent**: Generates improved code versions
- **Review Coordinator**: Synthesizes findings and generates reports
- **Decision Agent**: Determines whether to auto-apply or suggest fixes

## Notes

- Requires OpenAI API key for LLM-powered analysis and code rewriting
- Database storage enables historical code review analysis
- Test cases provided for easy testing and demonstration
- Supports Python and SQL code analysis (extensible to other languages)

