"""Base parser utilities for weather data parsing."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generic, List, Optional, TypeVar

from .token_stream import TokenStream

T = TypeVar("T")


class BaseParser(ABC, Generic[T]):
    """Abstract base class for weather parsers."""

    @abstractmethod
    def parse(self, token: str) -> Optional[T]:
        """Parse a single token into structured data."""
        raise NotImplementedError

    def extract_first(self, stream: TokenStream) -> Optional[T]:
        for i, token in enumerate(stream.tokens):
            result = self.parse(token)
            if result is not None:
                stream.pop(i)
                return result
        return None

    def extract_all(self, stream: TokenStream) -> List[T]:
        results: List[T] = []
        i = 0
        while i < len(stream.tokens):
            result = self.parse(stream.tokens[i])
            if result is not None:
                stream.pop(i)
                results.append(result)
            else:
                i += 1
        return results


class StopConditionMixin:
    stop_tokens: List[str] = []

    def should_stop(self, token: str) -> bool:
        return token in self.stop_tokens

    def extract_until_stop(self, stream: TokenStream) -> List[T]:
        results: List[T] = []
        i = 0
        while i < len(stream.tokens):
            if self.should_stop(stream.tokens[i]):
                break
            if hasattr(self, "parse"):
                result = self.parse(stream.tokens[i])  # type: ignore[attr-defined]
                if result is not None:
                    stream.pop(i)
                    results.append(result)
                    continue
            i += 1
        return results
