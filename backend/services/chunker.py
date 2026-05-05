"""
Chunker Service - Splits documents into chunks for embedding
Handles text segmentation with configurable size and overlap
"""
import re
from typing import List


class Chunker:
    """Service for chunking documents into embeddings-ready chunks"""
    
    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 64):
        """
        Initialize chunker
        
        Args:
            chunk_size: Size of each chunk in characters
            chunk_overlap: Overlap between chunks in characters
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def chunk_text(self, text: str) -> List[str]:
        """
        Split text into chunks with overlap
        
        Args:
            text: Text to chunk
        
        Returns:
            List of text chunks
        """
        if not text or len(text) == 0:
            return []
        
        chunks = []
        
        # Split by sentences first (more natural boundaries)
        sentences = self._split_into_sentences(text)
        
        current_chunk = ""
        
        for sentence in sentences:
            # If adding this sentence would exceed chunk_size, save current chunk
            if len(current_chunk) + len(sentence) > self.chunk_size and current_chunk:
                chunks.append(current_chunk.strip())
                
                # Create overlap by including the last part of previous chunk
                overlap_text = current_chunk[-self.chunk_overlap:] if len(current_chunk) > self.chunk_overlap else current_chunk
                current_chunk = overlap_text + " " + sentence
            else:
                current_chunk += " " + sentence if current_chunk else sentence
        
        # Add the last chunk
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences
        
        Args:
            text: Text to split
        
        Returns:
            List of sentences
        """
        # Split by common sentence endings, but preserve the delimiters
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        # Remove empty strings and clean up
        sentences = [s.strip() for s in sentences if s.strip()]
        
        return sentences
    
    def chunk_text_fixed_size(self, text: str) -> List[str]:
        """
        Split text into fixed-size chunks with overlap (alternative method)
        
        Args:
            text: Text to chunk
        
        Returns:
            List of text chunks
        """
        if not text or len(text) == 0:
            return []
        
        chunks = []
        start = 0
        
        while start < len(text):
            # Extract chunk
            end = min(start + self.chunk_size, len(text))
            chunk = text[start:end]
            chunks.append(chunk.strip())
            
            # Move start position (accounting for overlap)
            start += self.chunk_size - self.chunk_overlap
        
        return chunks
