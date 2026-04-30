"""Base LLM client interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseLLMClient(ABC):
    """Shared interface for optional language polishing providers."""

    @abstractmethod
    def enhance_response(self, context: dict[str, Any]) -> dict[str, Any]:
        """Return optional rewritten fields plus provider metadata."""
