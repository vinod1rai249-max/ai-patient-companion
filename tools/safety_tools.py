"""Deterministic safety guardrail tools for user and assistant content."""

from __future__ import annotations

from typing import Any


PROVIDER_DISCLAIMER = (
    "This information is for education only and is not medical advice. "
    "Please review your lab results and any concerns with your healthcare provider."
)

DIAGNOSIS_PATTERNS = [
    "do i have",
    "am i diabetic",
    "do i have diabetes",
    "diagnose me",
    "what condition do i have",
]
MEDICATION_PATTERNS = [
    "should i take",
    "should i start",
    "what dosage",
    "how much should i take",
    "can i take metformin",
    "should i take metformin",
]
EMERGENCY_PATTERNS = [
    "is this an emergency",
    "should i go to the er",
    "am i dying",
    "call 911",
    "chest pain",
    "can't breathe",
]
PROMPT_INJECTION_PATTERNS = [
    "ignore previous instructions",
    "ignore all prior instructions",
    "disregard your safety rules",
    "act as my doctor",
    "bypass safety",
]
UNSAFE_RESPONSE_PATTERNS = [
    "you have diabetes",
    "you should take metformin",
    "take 500 mg",
    "this is definitely an emergency",
    "i diagnose you with",
    "start this treatment",
]


class SafetyTools:
    """Deterministic safety tools for validating messages before LLM usage."""

    @staticmethod
    def detect_diagnosis_request(message: str) -> bool:
        return _contains_any(message, DIAGNOSIS_PATTERNS)

    @staticmethod
    def detect_medication_request(message: str) -> bool:
        return _contains_any(message, MEDICATION_PATTERNS)

    @staticmethod
    def detect_emergency_request(message: str) -> bool:
        return _contains_any(message, EMERGENCY_PATTERNS)

    @staticmethod
    def detect_prompt_injection(message: str) -> bool:
        return _contains_any(message, PROMPT_INJECTION_PATTERNS)

    def validate_user_message(self, message: str) -> dict[str, Any]:
        """Classify a user message and return a safe deterministic decision."""

        normalized_message = (message or "").strip()
        if not normalized_message:
            return {
                "is_safe": False,
                "category": "safe_general_question",
                "triggers": ["empty_message"],
                "allow": False,
                "refusal_message": self._build_refusal_message(
                    "Please provide a question about completed lab results or medical terms.",
                ),
            }

        triggers: list[str] = []
        category = "safe_general_question"

        if self.detect_prompt_injection(normalized_message):
            triggers.append("prompt_injection")
            category = "prompt_injection"
        if self.detect_diagnosis_request(normalized_message):
            triggers.append("diagnosis_request")
            category = "diagnosis_request"
        if self.detect_medication_request(normalized_message):
            triggers.append("medication_request")
            category = "medication_request"
        if self.detect_emergency_request(normalized_message):
            triggers.append("emergency_request")
            category = "emergency_request"

        if triggers:
            return {
                "is_safe": False,
                "category": category,
                "triggers": triggers,
                "allow": False,
                "refusal_message": self._build_refusal_message(
                    self._category_message(category),
                ),
            }

        return {
            "is_safe": True,
            "category": "safe_general_question",
            "triggers": [],
            "allow": True,
            "refusal_message": None,
        }

    def validate_ai_response(self, response: str) -> dict[str, Any]:
        """Validate assistant output against deterministic healthcare rules."""

        normalized_response = (response or "").strip()
        triggers: list[str] = []

        if _contains_any(normalized_response, UNSAFE_RESPONSE_PATTERNS):
            if "diagnose" in normalized_response.lower() or "you have" in normalized_response.lower():
                triggers.append("diagnosis_request")
            if "take" in normalized_response.lower() or "dosage" in normalized_response.lower() or "mg" in normalized_response.lower():
                triggers.append("medication_request")
            if "emergency" in normalized_response.lower():
                triggers.append("emergency_request")

        if PROVIDER_DISCLAIMER not in normalized_response:
            triggers.append("missing_provider_disclaimer")

        return {
            "is_valid": len(triggers) == 0,
            "triggers": triggers,
            "provider_disclaimer_present": PROVIDER_DISCLAIMER in normalized_response,
        }

    @staticmethod
    def _build_refusal_message(reason: str) -> str:
        return f"{reason} {PROVIDER_DISCLAIMER}"

    @staticmethod
    def _category_message(category: str) -> str:
        if category == "diagnosis_request":
            return "I cannot diagnose medical conditions."
        if category == "medication_request":
            return "I cannot recommend medications or dosage."
        if category == "emergency_request":
            return "I cannot assess emergency severity or tell you whether urgent care is needed."
        if category == "prompt_injection":
            return "I cannot ignore safety rules or act as a diagnosing clinician."
        return "I can help explain completed lab results in general language."


def detect_diagnosis_request(message: str) -> bool:
    return SafetyTools.detect_diagnosis_request(message)


def detect_medication_request(message: str) -> bool:
    return SafetyTools.detect_medication_request(message)


def detect_emergency_request(message: str) -> bool:
    return SafetyTools.detect_emergency_request(message)


def detect_prompt_injection(message: str) -> bool:
    return SafetyTools.detect_prompt_injection(message)


def validate_user_message(message: str) -> dict[str, Any]:
    return SafetyTools().validate_user_message(message)


def validate_ai_response(response: str) -> dict[str, Any]:
    return SafetyTools().validate_ai_response(response)


def _contains_any(message: str, patterns: list[str]) -> bool:
    normalized_message = (message or "").strip().lower()
    return any(pattern in normalized_message for pattern in patterns)
