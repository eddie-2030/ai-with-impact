from typing import Dict, Tuple, List
import numpy as np
from .utils import embed_texts

class LiteVectorStore:
    def __init__(self):
        self._store: Dict[str, Tuple[np.ndarray, dict]] = {}

    def upsert(self, key: str, text: str, metadata: dict):
        emb = embed_texts([text])[0]
        self._store[key] = (emb, metadata)

    def upsert_embedding(self, key: str, emb: np.ndarray, metadata: dict):
        self._store[key] = (emb, metadata)

    def query(self, text: str, top_k: int = 5) -> List[Tuple[str, float, dict]]:
        q = embed_texts([text])[0]
        sims = []
        for k, (e, m) in self._store.items():
            sims.append((k, float(e @ q), m))
        sims.sort(key=lambda x: x[1], reverse=True)
        return sims[:top_k]

VECTOR_DB = LiteVectorStore()
