import csv, os
from typing import List, Dict, Tuple
import numpy as np
from .utils import embed_texts

SKILLS_PATH = os.getenv("SKILLS_CSV", "data/ontology/skills.csv")

class Ontology:
    def __init__(self, path: str = SKILLS_PATH):
        self.path = path
        self.skills: List[Dict] = []
        self.labels: List[str] = []
        self._emb = None

    def load(self):
        self.skills.clear()
        self.labels.clear()
        with open(self.path) as f:
            reader = csv.DictReader(f)
            for r in reader:
                self.skills.append(r)
                self.labels.append(r["canonical_label"])
        self._emb = embed_texts(self.labels)

    def nearest(self, phrase: str, top_k: int = 1) -> List[Tuple[str, float]]:
        if self._emb is None:
            self.load()
        q = embed_texts([phrase])[0]
        sims = self._emb @ q
        idx = np.argsort(-sims)[:top_k]
        return [(self.labels[i], float(sims[i])) for i in idx]

ONTOLOGY = Ontology()
