"""
Qdrant vector store service
"""
import os
import time
from typing import List, Dict, Any
from qdrant_client import QdrantClient
from qdrant_client.http import models as rest_models


class QdrantStore:
    def __init__(self, collection_name: str = "textbooks"):
        qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
        api_key = os.getenv("QDRANT_API_KEY")
        # QdrantClient accepts url and api_key
        self.client = QdrantClient(url=qdrant_url, api_key=api_key)
        self.collection_name = collection_name

    def ensure_collection(self, vector_size: int):
        # Check existing collections
        try:
            collections = [c.name for c in self.client.get_collections().collections]
        except Exception:
            collections = []

        if self.collection_name in collections:
            # Optionally verify vector size; skipping strict check for now
            return

        # Create collection with cosine distance
        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=rest_models.VectorParams(size=vector_size, distance=rest_models.Distance.COSINE),
        )

    def upsert_chunks(self, upload_id: str, filename: str, chunks: List[str], embeddings: List[List[float]]):
        """Upsert chunk texts and vectors into Qdrant as points."""
        if not chunks:
            return
        if len(chunks) != len(embeddings):
            raise ValueError("Chunks and embeddings length mismatch")

        vector_size = len(embeddings[0])
        self.ensure_collection(vector_size)

        points = []
        for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
            point_id = f"{upload_id}::{i}"
            payload = {
                "upload_id": upload_id,
                "filename": filename,
                "sequence": i,
                "content": chunk,
            }
            points.append(rest_models.PointStruct(id=point_id, vector=emb, payload=payload))

        # Upsert in batches for large uploads
        batch_size = 128
        for start in range(0, len(points), batch_size):
            end = start + batch_size
            batch = points[start:end]
            self.client.upsert(collection_name=self.collection_name, points=batch)

    def search(self, query_vector: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        """Search for nearest chunks and return payloads with scores."""
        if not query_vector:
            return []
        try:
            results = self.client.search(collection_name=self.collection_name, query_vector=query_vector, limit=top_k)
        except Exception:
            return []

        out = []
        for r in results:
            payload = r.payload or {}
            out.append({
                "id": r.id,
                "score": r.score,
                "payload": payload,
            })
        return out
