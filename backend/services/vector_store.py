"""Qdrant vector store service."""

from typing import Any
from uuid import uuid4

from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, PointStruct, VectorParams

from backend.services.config import get_config


class VectorStore:
    def __init__(
        self,
        vector_size: int,
        url: str | None = None,
        collection_name: str | None = None,
    ) -> None:
        config = get_config()
        self.url = url or config.qdrant_url
        self.collection_name = collection_name or config.qdrant_collection
        self.vector_size = vector_size
        self.client = QdrantClient(url=self.url)

    def ensure_collection(self) -> None:
        collections = self.client.get_collections().collections
        exists = any(collection.name == self.collection_name for collection in collections)

        if not exists:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=self.vector_size, distance=Distance.COSINE),
            )

    def upsert_chunks(
        self,
        chunks: list[str],
        embeddings: list[list[float]],
        metadata: dict[str, Any],
    ) -> None:
        if len(chunks) != len(embeddings):
            raise ValueError("chunks and embeddings must have the same length.")

        self.ensure_collection()

        points = [
            PointStruct(
                id=str(uuid4()),
                vector=embedding,
                payload={
                    **metadata,
                    "chunk_index": index,
                    "text": chunk,
                },
            )
            for index, (chunk, embedding) in enumerate(zip(chunks, embeddings))
        ]

        self.client.upsert(collection_name=self.collection_name, points=points)

    def search(self, query_embedding: list[float], limit: int = 5) -> list[dict[str, Any]]:
        self.ensure_collection()
        if hasattr(self.client, "search"):
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=limit,
                with_payload=True,
            )
        else:
            query_response = self.client.query_points(
                collection_name=self.collection_name,
                query=query_embedding,
                limit=limit,
                with_payload=True,
            )
            results = query_response.points

        return [
            {
                "score": result.score,
                "text": (result.payload or {}).get("text", ""),
                "metadata": {
                    key: value
                    for key, value in (result.payload or {}).items()
                    if key != "text"
                },
            }
            for result in results
        ]
