from typing import Dict
from .vector_store import VECTOR_DB
def index_document(doc_id: str, text: str, metadata: Dict):
    VECTOR_DB.upsert(doc_id, text, metadata)
def retrieve(query: str, top_k: int = 5):
    return VECTOR_DB.query(query, top_k=top_k)
