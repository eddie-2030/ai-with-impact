import pickle, os
from typing import Dict, List, Tuple

class VectorStore:
    def __init__(self, path: str):
        self.path = path
        self.index = None  # (vectorizer, matrix, ids, titles, texts)

    def save(self, obj):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, 'wb') as f:
            pickle.dump(obj, f)

    def load(self):
        if not os.path.exists(self.path):
            return None
        with open(self.path, 'rb') as f:
            self.index = pickle.load(f)
        return self.index
