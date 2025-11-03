# Procurement Contract Analyzer: End-to-End Workflow & Technical Overview

## End-to-End Workflow

### Phase 1: Template Ingestion (`POST /ingest`)

**Purpose**: Prepare standard contract templates for semantic matching and comparison.

1. **Template Loading**
   - System loads contract templates from `data/templates/` directory (e.g., `master_service_agreement.md`, `standard_terms.md`)
   - Templates are registered in `TEMPLATE_REGISTRY` dictionary

2. **Text Extraction & Normalization**
   - Files are read using `read_text_any()` utility which supports:
     - PDF files (via `pdfminer.six`)
     - Word documents (via `python-docx`)
     - Markdown files (direct text extraction)
   - Markdown formatting is stripped using `MarkdownIt` parser to extract clean text

3. **Clause Segmentation**
   - Text is split into discrete clauses using `split_into_clauses()`
   - Pattern matching identifies clause headers:
     - Numbered sections (e.g., "1.", "2.1", "3.2.1")
     - Markdown headers (e.g., "### Section Title")
     - ALL-CAPS headers (e.g., "TERMS AND CONDITIONS")
   - Each clause is stored as `(clause_id:title, body_text)` tuple

4. **Vector Embedding Generation**
   - Each template clause is converted to a vector embedding using OpenAI's `text-embedding-3-small` model
   - Embeddings capture semantic meaning, not just keywords
   - Creates a high-dimensional vector representation (typically 1536 dimensions)

5. **Vector Store Persistence**
   - Embeddings, clause IDs, titles, and texts are stored in a pickle file (`artifacts/tfidf_store.pkl`)
   - Enables fast retrieval without re-computing embeddings on each request
   - Vector store maintains: `(retriever, embeddings_matrix, ids, titles, texts)`

**Output**: Indexed vector store ready for semantic clause matching.

---

### Phase 2: Contract Analysis (`POST /analyze`)

**Purpose**: Analyze an uploaded contract against the indexed templates to identify risks and deviations.

#### Step 1: Contract Upload & Preprocessing
- User uploads contract file (PDF, Word, or Markdown) via multipart form data
- System extracts file content using `read_text_any()`
- Text is normalized (markdown stripped if applicable)

#### Step 2: Contract Clause Extraction
- Contract text is segmented into clauses using the same `split_into_clauses()` logic
- Produces `contract_clauses` list of `(clause_id:title, body_text)` tuples
- Maintains structure similar to template clauses for comparison

#### Step 3: Contract Embedding Generation
- Each contract clause is converted to embeddings using the same OpenAI embedding model
- Creates a contract embedding matrix parallel to the template embedding matrix
- Builds a temporary index: `(contract_retriever, contract_embeddings)`

#### Step 4: Semantic Clause Matching
- **Vector Similarity Search**: For each template clause:
  1. The template clause embedding is used as a query vector
  2. Cosine similarity is calculated against all contract clause embeddings
  3. Top-k most similar contract clauses are retrieved (typically k=1 for best match)
  4. Returns indices and similarity scores

- **LLM Similarity Analysis**: For each matched pair:
  - GPT-4o-mini analyzes the template clause and matched contract clause
  - Calculates a refined similarity score (0-100)
  - Identifies key differences and risk indicators
  - Generates recommendations for the clause pair

#### Step 5: Context Preparation
- **Template Clauses**: Structured list of all template clauses with titles and bodies
- **Matched Clauses**: Contract clauses paired with their template counterparts, including:
  - Similarity scores
  - Matched clause text
  - Clause titles

#### Step 6: Comprehensive LLM Risk Assessment
- **Input to GPT-4o-mini**:
  - Full contract text
  - All template clauses (standard reference)
  - All matched clause pairs with similarity scores

- **LLM Analysis Tasks**:
  1. **Missing Clauses Detection**: Identifies critical template clauses absent from contract
  2. **High-Risk Clauses Identification**: Flags clauses with unfavorable terms
  3. **Deviation Analysis**: Detects how contract clauses differ from template standards
  4. **Global Risk Assessment**: Evaluates overall contract risks (legal, financial, operational)
  5. **Risk Score Calculation**: Generates 0-100 risk score with risk band classification

- **LLM Output Structure**:
  ```json
  {
    "overall_risk_score": 0-100,
    "risk_band": "LOW|MEDIUM|HIGH",
    "missing_clauses": ["clause1", "clause2"],
    "high_risk_clauses": [
      {
        "clause_title": "...",
        "risk_level": "...",
        "risk_factors": ["..."],
        "recommendations": ["..."]
      }
    ],
    "deviations": [
      {
        "clause_title": "...",
        "deviation_type": "...",
        "severity": "...",
        "description": "..."
      }
    ],
    "global_risks": ["risk1", "risk2"],
    "summary": "..."
  }
  ```

#### Step 7: Recommendation Generation
- LLM Risk Agent processes the analysis results
- Generates actionable recommendations based on:
  - Overall risk score
  - Missing clauses
  - High-risk clauses
  - Global risk factors

#### Step 8: Response Formatting
- All results are packaged into a JSON response
- Includes:
  - Overall risk score and band
  - Missing clauses list
  - Clause-by-clause comparison results
  - Risk flags and explanations
  - Actionable recommendations
  - Metadata (template name, LLM analysis flag)

**Output**: Comprehensive JSON risk assessment report ready for client consumption.

---

## Main Technical Elements

### 1. **RAG (Retrieval-Augmented Generation) Architecture**

#### Components:
- **Chunker** (`app/rag/chunker.py`): Segment documents into semantic clauses
- **Retriever** (`app/rag/retriever.py`): Semantic search using vector embeddings
- **Store** (`app/rag/store.py`): Persistent vector store for template embeddings

#### Technology Stack:
- **Embedding Model**: OpenAI `text-embedding-3-small` (1536 dimensions)
- **Similarity Metric**: Cosine similarity between vectors
- **Storage**: Pickle-based persistence for vector indices

#### Key Benefits:
- Semantic understanding beyond keyword matching
- Handles paraphrasing and different wording
- Accurate clause pairing even with structural differences

---

### 2. **LLM Integration Layer**

#### Components:
- **LLM Adapter** (`app/adapters/llm_adapter.py`): Unified interface to OpenAI API
- **LLM Risk Agent** (`app/analyzers/llm_risk_agent.py`): Specialized risk assessment logic

#### Models Used:
- **Embeddings**: `text-embedding-3-small` (fast, cost-effective for vector generation)
- **Chat/Analysis**: `gpt-4o-mini` (optimized for structured JSON output and analysis)

#### Key Features:
- **Clause Similarity Analysis**: Deep comparison of clause pairs
- **Risk Assessment**: Context-aware evaluation of entire contracts
- **Structured Output**: JSON-formatted responses for programmatic use
- **Error Handling**: Graceful fallbacks when LLM calls fail

#### API Integration:
- Uses OpenAI Python SDK (`openai` package)
- Environment-based configuration (API keys via `.env`)
- Temperature control (0.1 for consistent analysis)

---

### 3. **Document Processing Pipeline**

#### Supported Formats:
- **PDF**: `pdfminer.six` for text extraction
- **Word (.docx)**: `python-docx` for paragraph extraction
- **Markdown**: Direct text extraction with `MarkdownIt` parsing

#### Text Normalization:
- Markdown syntax stripping
- Encoding error handling
- Temporary file management for byte-based uploads

---

### 4. **FastAPI Web Framework**

#### Endpoints:
- `POST /ingest`: Template indexing endpoint
- `POST /analyze`: Contract analysis endpoint (multipart form data)

#### Features:
- Async request handling
- File upload support
- JSON response formatting
- Error handling with appropriate HTTP status codes
- API documentation via FastAPI's auto-generated docs

---

### 5. **Data Models (Pydantic Schemas)**

#### Schema Definitions (`app/models/schemas.py`):
- **ClauseComparison**: Structure for clause-by-clause analysis
- **AnalysisResult**: Complete analysis output structure
- **AnalysisRequest**: Request validation

#### Benefits:
- Type safety
- Automatic validation
- JSON serialization/deserialization
- API documentation generation

---

### 6. **Vector Storage System**

#### Architecture:
- **In-Memory Index**: Active vector store during runtime
- **Persistent Storage**: Pickle-based file storage
- **Lazy Loading**: Templates indexed on-demand if not pre-indexed

#### Storage Format:
- Tuple: `(retriever, embeddings_matrix, ids, titles, texts)`
- Enables fast similarity search without re-computation
- Supports multiple templates in single index

---

## Technical Flow Summary

```
1. Template Ingestion:
   Template Files → Text Extraction → Clause Segmentation → Embedding Generation → Vector Store

2. Contract Analysis:
   Upload Contract → Extract Text → Segment Clauses → Generate Embeddings → 
   Semantic Matching → LLM Similarity Analysis → Prepare Context → 
   LLM Risk Assessment → Generate Recommendations → Format Response

3. Key Algorithms:
   - Cosine Similarity for vector matching
   - Pattern Matching (regex) for clause segmentation
   - LLM prompting for structured JSON generation
```

---

## Performance Considerations

1. **Embedding Caching**: Template embeddings stored persistently to avoid re-computation
2. **Async Operations**: FastAPI async handling for concurrent requests
3. **Efficient Vector Operations**: NumPy-based matrix operations for similarity calculations
4. **Selective LLM Calls**: Embeddings first, then LLM analysis only on matched pairs

---

## Security & Configuration

- **API Key Management**: Secure storage via `.env` file (git-ignored)
- **Environment Variables**: Configurable models and paths
- **Error Handling**: Graceful degradation when LLM unavailable
- **Input Validation**: Pydantic schemas ensure data integrity

---

## Scalability Features

- **Modular Architecture**: Separated concerns (RAG, LLM, analysis)
- **Template Registry**: Easy addition of new contract templates
- **Vector Store Persistence**: Reduces computation on repeated template access
- **Stateless Design**: Can be containerized and scaled horizontally

