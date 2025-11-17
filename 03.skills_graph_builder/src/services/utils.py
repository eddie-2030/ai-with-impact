import os
import numpy as np
from typing import Iterable
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

def _client() -> OpenAI:
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY not set")
    return OpenAI(api_key=key)

def llm_complete(prompt: str, system: str = "You are a helpful assistant.") -> str:
    client = _client()
    resp = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[{"role":"system","content":system},{"role":"user","content":prompt}],
        temperature=0
    )
    return resp.choices[0].message.content.strip()

def embed_texts(texts: Iterable[str]) -> np.ndarray:
    texts = list(texts)
    if not texts:
        return np.zeros((0,1536), dtype=float)
    
    try:
        client = _client()
        resp = client.embeddings.create(model=EMBEDDING_MODEL, input=texts)
        vecs = [np.array(d.embedding, dtype=float) for d in resp.data]
        vecs = [v/(np.linalg.norm(v)+1e-12) for v in vecs]
        return np.vstack(vecs)
    except Exception as e:
        print(f"Warning: Could not generate embeddings ({e}). Using random embeddings.")
        # Generate random normalized embeddings as fallback
        vecs = [np.random.randn(1536).astype(float) for _ in texts]
        vecs = [v/(np.linalg.norm(v)+1e-12) for v in vecs]
        return np.vstack(vecs)

def cosine(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / ((np.linalg.norm(a)*np.linalg.norm(b))+1e-12))
