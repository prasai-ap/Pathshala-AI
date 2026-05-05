"""
Embedding service using sentence-transformers
"""
from typing import List
from sentence_transformers import SentenceTransformer
import numpy as np


class EmbeddingService:
    """Wraps a SentenceTransformer model for embeddings."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)
        self.dim = self.model.get_sentence_embedding_dimension()

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Return embeddings for list of texts as python lists."""
        if not texts:
            return []
        embeddings = self.model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
        # Ensure list of lists
        if isinstance(embeddings, np.ndarray):
            return embeddings.tolist()
        return [list(e) for e in embeddings]

    def embed_text(self, text: str) -> List[float]:
        return self.embed_texts([text])[0] if text else []
