import spacy
from typing import Tuple, Optional, List, Dict, Any
import numpy as np


class NLPTextSearch:
    """
    A class for performing semantic text searches using spaCy.
    Loads the spaCy model once for efficient repeated searches.
    """
    
    def __init__(self, model_name: str = "en_core_web_md"):
        """
        Initialize the NLP text searcher.
        
        Args:
            model_name: Name of the spaCy model to load (requires: python -m spacy download en_core_web_md)
        """
        self.nlp = spacy.load(model_name)
        self._processed_cache: Dict[str, Any] = {}  # Cache for processed documents
    
    def find_best_match(self, search_string: str, search_text: str, 
                       threshold: float = 0.7, use_cache: bool = True) -> Optional[Tuple[str, int, int, float]]:
        """
        Search for the best semantic match of search_string inside search_text.
        Returns a tuple of (matched substring, start index, end index, similarity score) or None if not found.
        
        Args:
            search_string: The text to search for
            search_text: The text to search within
            threshold: Minimum similarity score (0.0 to 1.0) to consider a match
            use_cache: Whether to cache processed documents for faster repeated searches
        
        Returns:
            Tuple of (matched_text, start_char, end_char, similarity_score) or None
        """
        if not search_string.strip() or not search_text.strip():
            return None
        
        # Process the search string to get its vector representation
        search_doc = self._get_processed_doc(search_string, use_cache)
        if not search_doc.has_vector:
            return None
        
        # Process the search text
        text_doc = self._get_processed_doc(search_text, use_cache)
        
        best_match = None
        best_similarity = threshold
        
        # Try different n-gram sizes for matching
        search_tokens = len(search_doc)
        max_ngram_size = min(search_tokens + 2, len(text_doc))
        
        # Process n-grams in reverse order (largest first) to prioritize longer matches
        # This helps with multi-line content where we want complete matches
        for ngram_size in range(max_ngram_size, 0, -1):
            for i in range(len(text_doc) - ngram_size + 1):
                # Extract n-gram span
                span = text_doc[i:i + ngram_size]
                
                if not span.has_vector:
                    continue
                
                # Calculate semantic similarity
                similarity = search_doc.similarity(span)
                
                # Add a small bias for longer matches (up to 0.05 bonus)
                # This helps prefer complete multi-line matches over partial matches
                length_bias = min(0.05, ngram_size / max(search_tokens, 1) * 0.05)
                adjusted_similarity = similarity + length_bias
                
                if adjusted_similarity > best_similarity:
                    best_similarity = adjusted_similarity
                    # Get character positions of the span
                    start_char = span.start_char
                    end_char = span.end_char
                    matched_text = search_text[start_char:end_char]
                    # Store the original similarity (without bias) in the result
                    best_match = (matched_text, start_char, end_char, similarity)
        
        return best_match
    
    def find_all_matches(self, search_string: str, search_text: str, 
                        threshold: float = 0.7, max_matches: int = 10) -> List[Tuple[str, int, int, float]]:
        """
        Find all semantic matches above the threshold, sorted by similarity score.
        
        Args:
            search_string: The text to search for
            search_text: The text to search within
            threshold: Minimum similarity score (0.0 to 1.0) to consider a match
            max_matches: Maximum number of matches to return
        
        Returns:
            List of tuples (matched_text, start_char, end_char, similarity_score) sorted by similarity
        """
        if not search_string.strip() or not search_text.strip():
            return []
        
        search_doc = self._get_processed_doc(search_string, True)
        if not search_doc.has_vector:
            return []
        
        text_doc = self._get_processed_doc(search_text, True)
        matches = []
        
        search_tokens = len(search_doc)
        max_ngram_size = min(search_tokens + 2, len(text_doc))
        
        # Process n-grams in reverse order to find longer matches first
        for ngram_size in range(max_ngram_size, 0, -1):
            for i in range(len(text_doc) - ngram_size + 1):
                span = text_doc[i:i + ngram_size]
                
                if not span.has_vector:
                    continue
                
                similarity = search_doc.similarity(span)
                
                if similarity >= threshold:
                    start_char = span.start_char
                    end_char = span.end_char
                    matched_text = search_text[start_char:end_char]
                    # Store original similarity, n-gram size for enhanced sorting
                    matches.append((matched_text, start_char, end_char, similarity, ngram_size))
        
        # Enhanced sorting: primarily by similarity, but prefer longer matches when close
        def sort_key(match):
            similarity = match[3]
            ngram_size = match[4]
            # Add small length bias to break ties in favor of longer matches
            length_bias = min(0.02, ngram_size / max(search_tokens, 1) * 0.02)
            return similarity + length_bias
        
        matches.sort(key=sort_key, reverse=True)
        
        # Return matches without the ngram_size, keeping original format
        return [(text, start, end, sim) for text, start, end, sim, _ in matches[:max_matches]]
    
    def _get_processed_doc(self, text: str, use_cache: bool = True):
        """Get a processed spaCy document, optionally using cache."""
        if use_cache and text in self._processed_cache:
            return self._processed_cache[text]
        
        doc = self.nlp(text)
        
        if use_cache:
            # Limit cache size to prevent memory issues
            if len(self._processed_cache) > 1000:
                # Remove oldest entries
                oldest_keys = list(self._processed_cache.keys())[:100]
                for key in oldest_keys:
                    del self._processed_cache[key]
            self._processed_cache[text] = doc
        
        return doc
    
    def clear_cache(self):
        """Clear the document processing cache."""
        self._processed_cache.clear()


# Convenience function for simple usage without creating a class instance
def find_best_match(search_string: str, search_text: str, threshold: float = 0.7) -> Optional[Tuple[str, int, int, float]]:
    """
    Convenience function for one-off searches. For multiple searches, use NLPTextSearch class directly.
    """
    searcher = NLPTextSearch()
    return searcher.find_best_match(search_string, search_text, threshold, use_cache=False)
