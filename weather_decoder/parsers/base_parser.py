"""Base parser class for weather data parsing

This module defines the abstract base class that all weather parsers should inherit from.
It establishes a consistent interface and provides common functionality for parsing
weather report tokens.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, List, Optional, TypeVar

# Type variable for parser result types
T = TypeVar('T')


class BaseParser(ABC, Generic[T]):
    """Abstract base class for weather data parsers
    
    All specialized parsers (wind, visibility, weather, etc.) should inherit
    from this class to ensure a consistent interface.
    
    Type Parameters:
        T: The type of data returned by the parser (usually Dict or List[Dict])
    
    Design Principles:
        1. `parse()` - Pure function that parses a single token, returns None if no match
        2. `extract()` - Stateful extraction that removes matched tokens from the list
        3. Parsers should be stateless where possible
    """

    @abstractmethod
    def parse(self, token: str) -> Optional[T]:
        """Parse a single token into structured data
        
        This is a pure function that should not modify any state.
        It attempts to parse the given token and returns structured
        data if successful, or None if the token doesn't match.
        
        Args:
            token: A single token from the weather report
            
        Returns:
            Parsed data structure if the token matches, None otherwise
        """
        pass

    def extract(self, parts: List[str]) -> Optional[T]:
        """Extract and remove matching token(s) from the parts list
        
        This method iterates through the parts list, attempts to parse
        each token, and removes successfully parsed tokens from the list.
        
        Note: This method modifies the input list in place by removing
        parsed tokens. This is intentional to prevent double-processing
        of tokens.
        
        Args:
            parts: List of tokens from the weather report (modified in place)
            
        Returns:
            First successfully parsed data, or None if no tokens match
        """
        for i, part in enumerate(parts):
            result = self.parse(part)
            if result is not None:
                parts.pop(i)
                return result
        return None

    def extract_all(self, parts: List[str]) -> List[T]:
        """Extract all matching tokens from the parts list
        
        Similar to extract(), but continues to find all matching tokens
        instead of stopping at the first match.
        
        Args:
            parts: List of tokens from the weather report (modified in place)
            
        Returns:
            List of all successfully parsed data structures
        """
        results: List[T] = []
        i = 0
        while i < len(parts):
            result = self.parse(parts[i])
            if result is not None:
                parts.pop(i)
                results.append(result)
                # Don't increment i since we removed the current element
            else:
                i += 1
        return results


class TokenParser(BaseParser[Dict]):
    """Base class for parsers that return a single dictionary result
    
    This is the most common parser type, used for parsing individual
    weather elements like wind, visibility, pressure, etc.
    """
    pass


class MultiTokenParser(BaseParser[List[Dict]]):
    """Base class for parsers that may need multiple tokens
    
    Some weather elements span multiple tokens (e.g., "1 1/2SM" for
    visibility). This base class provides additional methods for
    handling multi-token parsing.
    """
    
    def parse_with_lookahead(
        self, 
        parts: List[str], 
        start_index: int
    ) -> tuple[Optional[List[Dict]], int]:
        """Parse tokens starting at the given index with lookahead
        
        This method allows parsers to consume multiple tokens when needed.
        
        Args:
            parts: List of tokens from the weather report
            start_index: Index to start parsing from
            
        Returns:
            Tuple of (parsed_data, tokens_consumed)
            If no match, returns (None, 0)
        """
        # Default implementation just parses single token
        if start_index < len(parts):
            result = self.parse(parts[start_index])
            if result is not None:
                return ([result] if not isinstance(result, list) else result, 1)
        return (None, 0)


class StopConditionMixin:
    """Mixin that adds stop condition checking for parsers
    
    Some parsers should stop when they encounter certain tokens
    (e.g., trend indicators like TEMPO, BECMG, NOSIG).
    """
    
    # Override in subclasses to define stop tokens
    stop_tokens: List[str] = []
    
    def should_stop(self, token: str) -> bool:
        """Check if parsing should stop at this token
        
        Args:
            token: The token to check
            
        Returns:
            True if parsing should stop, False otherwise
        """
        return token in self.stop_tokens
    
    def extract_until_stop(self, parts: List[str]) -> List[Any]:
        """Extract all matching tokens until a stop token is encountered
        
        Args:
            parts: List of tokens from the weather report (modified in place)
            
        Returns:
            List of all successfully parsed data structures before stop token
        """
        results: List[Any] = []
        i = 0
        while i < len(parts):
            if self.should_stop(parts[i]):
                break
            # This assumes the class also inherits from BaseParser
            if hasattr(self, 'parse'):
                result = self.parse(parts[i])  # type: ignore
                if result is not None:
                    parts.pop(i)
                    results.append(result)
                    continue
            i += 1
        return results

