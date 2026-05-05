"""Text chunking service."""


def chunk_text(text: str, chunk_size: int = 900, overlap: int = 150) -> list[str]:
    normalized_text = " ".join(text.split())
    if not normalized_text:
        return []

    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than 0.")
    if overlap < 0:
        raise ValueError("overlap must be 0 or greater.")
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size.")

    chunks: list[str] = []
    start = 0

    while start < len(normalized_text):
        end = min(start + chunk_size, len(normalized_text))
        chunks.append(normalized_text[start:end].strip())

        if end == len(normalized_text):
            break

        start = end - overlap

    return chunks
