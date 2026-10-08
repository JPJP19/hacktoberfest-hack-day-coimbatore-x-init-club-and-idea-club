from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List


class EmbeddingService:
    """Lazy-loading sentence-transformer wrapper."""

    def __init__(self):
        self.model: SentenceTransformer | None = None

    def _get_model(self) -> SentenceTransformer:
        if self.model is None:
            self.model = SentenceTransformer("all-MiniLM-L6-v2")
        return self.model

    def encode(self, text: str) -> List[float]:
        model = self._get_model()
        emb = model.encode(text, normalize_embeddings=True)
        return emb.tolist()

    def cosine_similarity(self, a: List[float], b: List[float]) -> float:
        va, vb = np.array(a), np.array(b)
        denom = np.linalg.norm(va) * np.linalg.norm(vb) + 1e-8
        return float(np.dot(va, vb) / denom)


embedding_service = EmbeddingService()
