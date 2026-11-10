import csv, os
from typing import List, Dict, Tuple
import numpy as np
from .utils import ProviderUnavailable, embed_texts

SKILLS_PATH = os.getenv("SKILLS_CSV", "data/ontology/skills.csv")

class Ontology:
    def __init__(self, path: str = SKILLS_PATH):
        self.path = path
        self.skills: List[Dict] = []
        self.labels: List[str] = []
        self._emb = None

    def load(self):
        with open(self.path, encoding="utf-8") as f:
            self.skills = [row for row in csv.DictReader(f) if row["canonical_label"].strip()]
        self.labels = [row["canonical_label"] for row in self.skills]
        self._emb = None

    def nearest(self, phrase: str, top_k: int = 1) -> List[Tuple[str, float]]:
        if not self.labels:
            self.load()
        if not self.labels or not phrase.strip():
            return []
        labels = self.labels
        embeddings = self._emb
        if embeddings is None:
            embeddings = embed_texts(labels)
            self._emb = embeddings
        query = embed_texts([phrase])[0]
        if embeddings.shape[1] != query.shape[0]:
            raise ProviderUnavailable(
                "provider_invalid_response", "The provider returned inconsistent embedding dimensions."
            )
        sims = embeddings @ query
        idx = np.argsort(-sims)[:top_k]
        return [(labels[i], float(sims[i])) for i in idx]

ONTOLOGY = Ontology()
