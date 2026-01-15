"""Token stream utility for parsing weather report tokens."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Optional


@dataclass
class TokenStream:
    tokens: List[str]

    @classmethod
    def from_text(cls, text: str) -> "TokenStream":
        return cls(text.split())

    def __len__(self) -> int:
        return len(self.tokens)

    def peek(self, offset: int = 0) -> Optional[str]:
        index = offset
        if index < 0 or index >= len(self.tokens):
            return None
        return self.tokens[index]

    def pop(self, index: int = 0) -> str:
        return self.tokens.pop(index)

    def consume_if(self, predicate: Callable[[str], bool]) -> Optional[str]:
        for i, token in enumerate(self.tokens):
            if predicate(token):
                return self.tokens.pop(i)
        return None

    def consume_all(self, predicate: Callable[[str], bool]) -> List[str]:
        matches: List[str] = []
        i = 0
        while i < len(self.tokens):
            if predicate(self.tokens[i]):
                matches.append(self.tokens.pop(i))
            else:
                i += 1
        return matches

    def remaining(self) -> List[str]:
        return list(self.tokens)
