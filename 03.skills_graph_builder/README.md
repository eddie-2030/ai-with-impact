# Skills Graph Case Study - LLM-Powered Career Development Platform

A comprehensive skills graph system that uses LLMs to analyze people's skills, match them to roles, and generate personalized learning plans for career development.

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- OpenAI API Key
- Virtual environment (recommended)

### Installation & Setup

1. **Clone and setup environment:**
   ```bash
   git clone <repository-url>
   cd skills_graph_case_study_llm_openai
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure API key:**
   ```bash
   cp .env.example .env
   # Edit .env and add your OpenAI API key:
   # OPENAI_API_KEY=sk-proj-your-key-here
   ```

4. **Generate synthetic data:**
   ```bash
   python scripts/generate_synth_data.py
   ```

5. **Start the application:**
   ```bash
   # Terminal 1: Start backend API
   source .venv/bin/activate
   export OPENAI_API_KEY=sk-proj-your-key-here
   PYTHONPATH=/path/to/project python -m uvicorn src.app:app --host 0.0.0.0 --port 8000
   
   # Terminal 2: Start Streamlit UI
   source .venv/bin/activate
   export OPENAI_API_KEY=sk-proj-your-key-here
   PYTHONPATH=/path/to/project streamlit run ui/streamlit_app.py
   ```

6. **Access the application:**
   - Streamlit UI: http://localhost:8501
   - API Documentation: http://localhost:8000/docs

## 🏗️ Architecture & Code Structure

### Project Structure
```
skills_graph_case_study_llm_openai/
├── data/                          # Data storage
│   ├── ontology/                  # Skills taxonomy
│   │   └── skills.csv
│   ├── roles/                     # Role definitions
│   │   └── role_skill_requirements.csv
│   └── samples/                   # Generated synthetic data
│       ├── people.jsonl           # Person profiles
│       ├── projects/              # Project descriptions
│       └── resumes/               # Resume text files
├── src/                           # Core application code
│   ├── agents/                    # LLM-powered agents
│   │   ├── profile_parser.py      # Extract skills from text
│   │   ├── taxonomy_mapper.py     # Map skills to taxonomy
│   │   ├── role_profiler.py       # Role matching logic
│   │   ├── gap_coach.py           # Skill gap analysis
│   │   ├── roi_estimator.py       # Learning ROI estimation
│   │   └── guard.py               # Content filtering
│   ├── orchestrator/              # Workflow orchestration
│   │   └── graph.py               # Main workflow functions
│   ├── services/                  # Core services
│   │   ├── graph_store.py         # Graph database (NetworkX)
│   │   ├── vector_store.py        # Vector embeddings storage
│   │   ├── rag.py                 # Retrieval-augmented generation
│   │   ├── ontology.py            # Skills taxonomy management
│   │   ├── eval.py                # MLflow logging (optional)
│   │   ├── utils.py               # OpenAI API utilities
│   │   └── schemas.py              # Pydantic data models
│   └── app.py                     # FastAPI application
├── scripts/                       # Utility scripts
│   ├── generate_synth_data.py     # Generate synthetic people data
│   └── load_seed_data.py          # Load data into graph (deprecated)
├── ui/                            # User interface
│   └── streamlit_app.py           # Streamlit web interface
├── requirements.txt               # Python dependencies
├── .env.example                   # Environment variables template
└── README.md                      # This file
```

### Core Components

#### 1. **Graph Store** (`src/services/graph_store.py`)
- In-memory graph database using NetworkX
- Stores people, skills, and roles as nodes
- Manages relationships between entities
- Provides query methods for the API

#### 2. **LLM Agents** (`src/agents/`)
- **Profile Parser**: Extracts skills from project/resume text using LLM
- **Taxonomy Mapper**: Maps extracted skills to standardized taxonomy
- **Role Profiler**: Computes skill-based role matches
- **Gap Coach**: Generates personalized learning plans
- **ROI Estimator**: Estimates learning investment returns

#### 3. **Vector Store** (`src/services/vector_store.py`)
- Stores document embeddings for semantic search
- Uses OpenAI embeddings for text similarity
- Enables RAG (Retrieval-Augmented Generation) capabilities

#### 4. **API Layer** (`src/app.py`)
- FastAPI REST API with automatic data loading
- Endpoints for people, roles, skills, and recommendations
- Built-in startup data ingestion from generated files

#### 5. **Web Interface** (`ui/streamlit_app.py`)
- Interactive Streamlit dashboard
- People selection and skill visualization
- Role matching and gap analysis tools

## 🔄 Data Flow

1. **Data Generation**: `generate_synth_data.py` creates 50 synthetic people with projects/resumes
2. **API Startup**: `app.py` automatically loads people data and role definitions
3. **Skill Extraction**: Profile parser uses LLM to extract skills from text
4. **Taxonomy Mapping**: Skills are mapped to standardized taxonomy
5. **Graph Storage**: People, skills, and relationships stored in NetworkX graph
6. **API Serving**: FastAPI serves data to Streamlit UI
7. **User Interaction**: Streamlit provides interactive exploration and analysis

## 🛠️ Key Features

### Skills Graph Builder
- **Automatic Skill Extraction**: Uses LLM to parse project descriptions and resumes
- **Taxonomy Mapping**: Standardizes skills across different naming conventions
- **Relationship Modeling**: Captures person-skill and role-skill relationships

### Role Matching Engine
- **Skill-based Matching**: Computes compatibility scores between people and roles
- **Weighted Requirements**: Considers skill importance and must-have requirements
- **Top-K Recommendations**: Provides ranked list of best role matches

### Gap Analysis & Coaching
- **Skill Gap Identification**: Identifies missing skills for target roles
- **Personalized Learning Plans**: Generates actionable learning recommendations
- **ROI Estimation**: Estimates time and effort investment for skill development

### Interactive Dashboard
- **People Browser**: Explore all people and their skills
- **Role Explorer**: View role requirements and skill mappings
- **Match Analysis**: Interactive role matching and gap analysis
- **Plan Generation**: Create and view personalized learning plans

## 🔧 Configuration

### Environment Variables
```bash
# Required
OPENAI_API_KEY=sk-proj-your-key-here

# Optional (defaults shown)
LLM_MODEL=gpt-4o-mini
EMBEDDING_MODEL=text-embedding-3-small
MLFLOW_TRACKING_URI=file:./mlruns
MLFLOW_EXPERIMENT=skills_graph_case_study
```

### API Endpoints
- `GET /health` - Health check
- `GET /roles` - List all roles with requirements
- `GET /persons` - List all people with profiles
- `GET /person/{person_id}/skills` - Get person's skills
- `GET /roles/matches?person_id={id}&top_k={n}` - Get role matches
- `GET /recommendations/{person_id}?role_id={id}` - Get learning plan

## 🚨 Troubleshooting

### Common Issues

1. **"No people data" in Streamlit UI**
   - Ensure API server is running with data loaded
   - Check that `generate_synth_data.py` was run successfully
   - Verify API key is set correctly

2. **OpenAI API errors**
   - Verify API key is valid and has credits
   - Check rate limits and usage quotas
   - Ensure network connectivity

3. **Missing dependencies**
   - Run `pip install -r requirements.txt`
   - Activate virtual environment before running

4. **Port conflicts**
   - API runs on port 8000, Streamlit on 8501
   - Kill existing processes: `pkill -f uvicorn` or `pkill -f streamlit`

### Development Notes

- **Data Persistence**: Graph data is in-memory and resets on API restart
- **MLflow Integration**: Optional logging for experiment tracking
- **Error Handling**: Graceful fallbacks for missing API keys or dependencies
- **Performance**: Designed for demo/development use with synthetic data

## 📊 Sample Data

The system generates 50 synthetic people with:
- **Diverse Roles**: Data Analysts, ML Engineers, Platform Engineers, etc.
- **Realistic Skills**: Python, SQL, AWS, MLOps, LLMOps, etc.
- **Project Descriptions**: Contextual skill evidence from work experience
- **Resume Content**: Structured skill bullet points

## 🔮 Future Enhancements

- **Persistent Storage**: Database integration for production use
- **Real Data Integration**: Connect to HR systems and learning platforms
- **Advanced Analytics**: Skill trend analysis and market insights
- **Learning Path Optimization**: AI-powered curriculum generation
- **Team Analysis**: Group skill gap analysis and team building

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

---

**Built with ❤️ using FastAPI, Streamlit, NetworkX, and OpenAI's GPT models**