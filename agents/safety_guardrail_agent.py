"""Deterministic safety guardrail agent."""

from __future__ import annotations

from typing import Any

from tools.safety_tools import PROVIDER_DISCLAIMER, SafetyTools


class SafetyGuardrailAgent:
    """Validate user input and final output using deterministic safety tools."""

    def __init__(self, safety_tools: SafetyTools | None = None) -> None:
        self.safety_tools = safety_tools or SafetyTools()

    def validate_user_message(self, message: str) -> dict[str, Any]:
        return self.safety_tools.validate_user_message(message)

    def validate_final_response(self, response: str) -> dict[str, Any]:
        return self.safety_tools.validate_ai_response(response)

    def build_blocked_response(self, validation: dict[str, Any]) -> dict[str, Any]:
        refusal_message = validation.get("refusal_message") or PROVIDER_DISCLAIMER
        return {
            "reply": refusal_message,
            "disclaimer": PROVIDER_DISCLAIMER,
            "safety": {
                "is_safe": False,
                "triggers": validation.get("triggers", []),
                "disclaimer_added": True,
            },
            "safety_status": "FLAGGED",
        }
