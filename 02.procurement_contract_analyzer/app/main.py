from fastapi import FastAPI, UploadFile, File, Form
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from typing import List, Dict, Tuple
import os, json
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from app.utils.io import (
    MAX_UPLOAD_BYTES,
    DocumentTooLarge,
    InvalidDocument,
    UnsupportedDocument,
    markdown_to_text,
    read_text_any,
    read_upload_text,
)
from app.rag.chunker import split_into_clauses
from app.rag.retriever import build_index, search
from app.analyzers.llm_risk_agent import LLMRiskAgent
from app.adapters.llm_adapter import LLMAdapter

DATA_DIR = os.environ.get('DATA_DIR', 'data')

app = FastAPI(title="Procurement Contract Analyzer", version="0.1.0")

TEMPLATE_REGISTRY = {
    "master_service_agreement": os.path.join(DATA_DIR, "templates", "master_service_agreement.md"),
    "standard_terms": os.path.join(DATA_DIR, "templates", "standard_terms.md"),
}

template_index = None

# Initialize LLM components
try:
    llm_adapter = LLMAdapter()
    llm_risk_agent = LLMRiskAgent(llm_adapter)
    llm_available = True
except Exception as e:
    print(f"LLM not available: {e}")
    llm_adapter = None
    llm_risk_agent = None
    llm_available = False

def load_templates() -> Dict[str, Dict]:
    templates = {}
    for name, path in TEMPLATE_REGISTRY.items():
        if not os.path.exists(path):
            continue
        text = read_text_any(path)
        text = markdown_to_text(text)
        clauses = split_into_clauses(text)
        templates[name] = {"path": path, "clauses": clauses}
    return templates

TEMPLATES = load_templates()

def build_template_index(templates: Dict[str, Dict]):
    global template_index
    texts = [body for template in templates.values() for _, body in template["clauses"]]
    # The retriever contains a live SDK client. Keep it in memory.
    template_index = build_index(texts, llm_adapter)

@app.post('/ingest')
def ingest():
    global TEMPLATES
    templates = load_templates()
    build_template_index(templates)
    TEMPLATES = templates
    return {"ok": True, "templates": list(TEMPLATES.keys()), "clauses_indexed": sum(len(t["clauses"]) for t in TEMPLATES.values())}

def grade_band(score: float) -> str:
    if score >= 80: return "LOW"
    if score >= 60: return "MEDIUM"
    return "HIGH"

@app.post('/analyze')
async def analyze_contract(template_name: str = Form(default="master_service_agreement"),
                           file: UploadFile = File(...)):
    try:
        content = await file.read(MAX_UPLOAD_BYTES + 1)
        contract_text = await run_in_threadpool(read_upload_text, content, file.filename)
    except DocumentTooLarge as exc:
        return JSONResponse({"error": str(exc)}, status_code=413)
    except UnsupportedDocument as exc:
        return JSONResponse({"error": str(exc)}, status_code=415)
    except InvalidDocument as exc:
        return JSONResponse({"error": str(exc)}, status_code=422)

    contract_text = markdown_to_text(contract_text)
    contract_clauses = [(title, body) for title, body in split_into_clauses(contract_text) if body]
    if not contract_clauses:
        return JSONResponse({"error": "The document does not contain readable contract clauses."}, status_code=422)

    if not TEMPLATES:
        return JSONResponse({"error": "No templates loaded"}, status_code=400)
    tpl = TEMPLATES.get(template_name)
    if not tpl:
        return JSONResponse({"error": f"Unknown template '{template_name}'"}, status_code=400)

    if not llm_available:
        return JSONResponse({
            "error": "LLM not available. Please set OPENAI_API_KEY in .env file or environment variables."
        }, status_code=500)
    if template_index is None:
        build_template_index(TEMPLATES)

    return await analyze_with_llm_agent(contract_text, contract_clauses, tpl, template_name)

async def analyze_with_llm_agent(contract_text: str, contract_clauses: List[Tuple], 
                                tpl: Dict, template_name: str) -> JSONResponse:
    """Analyze contract using LLM agent."""
    try:
        # Prepare template clauses for LLM analysis
        template_clauses = []
        for cid_title, body in tpl['clauses']:
            template_clauses.append({
                'title': cid_title.split(':', 1)[-1],
                'body': body
            })
        
        # Prepare matched clauses using LLM embeddings
        matched_clauses = []
        if template_index is not None:
            # Build contract index using LLM embeddings
            contract_texts = [c[1] for c in contract_clauses]
            contract_retriever, contract_embeddings = build_index(contract_texts, llm_adapter)
            
            for cid_title, tpl_body in tpl['clauses']:
                # Find best matching contract clause
                top_idx, top_scores = search(contract_retriever, contract_embeddings, [tpl_body], topk=1)
                if top_idx.shape[1] > 0:
                    idx = int(top_idx[0][0])
                    candidate_text = contract_clauses[idx][1]
                    # Use LLM to calculate similarity
                    similarity_analysis = llm_adapter.analyze_clause_similarity(tpl_body, candidate_text)
                    similarity_score = similarity_analysis.get('similarity_score', 50.0)
                    
                    matched_clauses.append({
                        'title': cid_title.split(':', 1)[-1],
                        'body': candidate_text,
                        'similarity': similarity_score
                    })
        
        # Use LLM agent for comprehensive analysis
        result = llm_risk_agent.analyze_contract(contract_text, template_clauses, matched_clauses)
        result.template_name = template_name
        
        # Add recommendations
        recommendations = llm_risk_agent.generate_recommendations(result)
        result_dict = json.loads(result.model_dump_json())
        result_dict['recommendations'] = recommendations
        result_dict['llm_analysis'] = True
        
        return JSONResponse(result_dict)
        
    except Exception as e:
        return JSONResponse({
            "error": f"LLM analysis failed: {str(e)}",
            "fallback_available": True
        }, status_code=500)

# Removed traditional TF-IDF method - now using LLM-only approach
