"""Embedding service using sentence-transformers."""

from functools import lru_cache

from sentence_transformers import SentenceTransformer

from backend.services.config import get_config


class EmbeddingService:
    def __init__(self, model_name: str | None = None) -> None:
        config = get_config()
        self.model_name = model_name or config.embedding_model
        self.model = SentenceTransformer(self.model_name)
        self.dimension = self.model.get_sentence_embedding_dimension()

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        embeddings = self.model.encode(texts, normalize_embeddings=True)
        return embeddings.tolist()

    def embed_query(self, question: str) -> list[float]:
        return self.embed_texts([question])[0]


@lru_cache(maxsize=1)
def get_embedding_service() -> EmbeddingService:
    return EmbeddingService()
