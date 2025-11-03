from typing import List, Tuple, Dict
import numpy as np
from app.adapters.llm_adapter import LLMAdapter

class LLMRetriever:
    def __init__(self, llm_adapter: LLMAdapter):
        self.llm_adapter = llm_adapter
        self.embeddings = None
        self.texts = None
    
    def build_index(self, doc_texts: List[str]) -> np.ndarray:
        """Build index using LLM embeddings instead of TF-IDF."""
        self.texts = doc_texts
        self.embeddings = self.llm_adapter.get_embeddings(doc_texts)
        return self.embeddings
    
    def search(self, query_texts: List[str], topk: int = 1) -> Tuple[np.ndarray, np.ndarray]:
        """Search for similar documents using LLM embeddings."""
        if self.embeddings is None:
            raise ValueError("Index not built. Call build_index first.")
        
        query_embeddings = self.llm_adapter.get_embeddings(query_texts)
        top_idx, top_scores = self.llm_adapter.search_similar(
            query_embeddings, self.embeddings, topk
        )
        return top_idx, top_scores

# Backward compatibility functions
def build_index(doc_texts: List[str], llm_adapter: LLMAdapter = None):
    """Build index using LLM embeddings."""
    if llm_adapter is None:
        llm_adapter = LLMAdapter()
    retriever = LLMRetriever(llm_adapter)
    embeddings = retriever.build_index(doc_texts)
    return retriever, embeddings

def search(retriever, embeddings, query_texts: List[str], topk: int = 1):
    """Search using LLM embeddings."""
    return retriever.search(query_texts, topk)
