from __future__ import annotations

import os
from typing import List, Tuple
import numpy as np
from sentence_transformers import SentenceTransformer
import logging

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for finding the most similar response using sentence embeddings."""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize the embedding service with a lightweight model.
        
        Args:
            model_name: The sentence transformer model to use. 
                       'all-MiniLM-L6-v2' is lightweight and fast.
        """
        self.model_name = model_name
        self.model = None
        self.responses = []
        self.response_embeddings = None
        self._load_model()
    
    def _load_model(self) -> None:
        """Load the sentence transformer model."""
        try:
            logger.info(f"Loading embedding model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
            logger.info("Embedding model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise
    
    def load_responses(self, responses: List[str]) -> None:
        """
        Load and encode the response list for similarity matching.
        
        Args:
            responses: List of response strings to match against
        """
        if not self.model:
            raise RuntimeError("Model not loaded. Call _load_model() first.")
        
        self.responses = responses
        logger.info(f"Encoding {len(responses)} responses")
        
        try:
            # Encode all responses at once for efficiency
            self.response_embeddings = self.model.encode(responses)
            logger.info("Responses encoded successfully")
        except Exception as e:
            logger.error(f"Failed to encode responses: {e}")
            raise
    
    def find_most_similar(self, query: str, top_k: int = 1) -> List[Tuple[str, float]]:
        """
        Find the most similar response(s) to the given query.
        
        Args:
            query: The input text to find similar responses for
            top_k: Number of top similar responses to return
            
        Returns:
            List of tuples containing (response_text, similarity_score)
        """
        if not self.model or self.response_embeddings is None:
            raise RuntimeError("Model or responses not loaded")
        
        if not self.responses:
            return []
        
        try:
            # Encode the query
            query_embedding = self.model.encode([query])
            
            # Calculate cosine similarity
            similarities = np.dot(self.response_embeddings, query_embedding.T).flatten()
            
            # Get top-k most similar responses
            top_indices = np.argsort(similarities)[::-1][:top_k]
            
            results = []
            for idx in top_indices:
                response = self.responses[idx]
                similarity = float(similarities[idx])
                results.append((response, similarity))
            
            return results
            
        except Exception as e:
            logger.error(f"Error finding similar responses: {e}")
            return []
    
    def get_best_response(self, query: str, min_similarity: float = 0.3) -> str | None:
        """
        Get the best matching response, or None if no good match is found.
        
        Args:
            query: The input text to find similar responses for
            min_similarity: Minimum similarity threshold (0-1) for a valid match
            
        Returns:
            The best matching response string, or None if no good match
        """
        results = self.find_most_similar(query, top_k=1)
        
        if not results:
            return None
        
        response, similarity = results[0]
        
        if similarity >= min_similarity:
            logger.info(f"Found good match (similarity: {similarity:.3f}): '{query}' -> '{response}'")
            return response
        else:
            logger.info(f"No good match found (best similarity: {similarity:.3f} < {min_similarity})")
            return None


# Global instance for easy access
_embedding_service = None


def get_embedding_service() -> EmbeddingService:
    """Get the global embedding service instance."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service


def initialize_embedding_service(responses: List[str]) -> None:
    """
    Initialize the global embedding service with responses.
    
    Args:
        responses: List of response strings to match against
    """
    service = get_embedding_service()
    service.load_responses(responses)
    logger.info(f"Embedding service initialized with {len(responses)} responses")
