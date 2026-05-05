"""
Retriever Agent - Retrieves relevant context from vector store
Uses Qdrant for semantic search
"""


class RetrieverAgent:
    """Agent for retrieving relevant documents from vector store

    This version accepts an embedding service and a vector store (QdrantStore)
    and exposes a convenience method to return top-k matching chunks with
    their metadata.
    """

    def __init__(self, embedding_service, vector_store_client):
        self.embedding = embedding_service
        self.vector_store = vector_store_client

    async def retrieve_context(self, query: str, top_k: int = 5):
        """
        Retrieve relevant context for a query

        Returns a list of dicts: {id, score, content, upload_id, filename, sequence}
        """
        if not query or not query.strip():
            return []

        # Embed the query
        try:
            qvec = self.embedding.embed_text(query)
        except Exception:
            return []

        # Query vector store
        try:
            results = self.vector_store.search(query_vector=qvec, top_k=top_k)
        except Exception:
            return []

        # Normalize output
        out = []
        for r in results:
            payload = r.get("payload", {})
            out.append({
                "id": r.get("id"),
                "score": r.get("score"),
                "content": payload.get("content"),
                "upload_id": payload.get("upload_id"),
                "filename": payload.get("filename"),
                "sequence": payload.get("sequence"),
            })

        return out
