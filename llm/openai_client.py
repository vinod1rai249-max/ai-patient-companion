"""OpenRouter-backed client using the OpenAI SDK."""

from __future__ import annotations

import json
from typing import Any

from backend.config import Settings, get_settings
from llm.base import BaseLLMClient

try:
    from tenacity import retry, stop_after_attempt, wait_fixed
except ModuleNotFoundError:  # pragma: no cover - optional dependency fallback
    def retry(*args, **kwargs):  # type: ignore[override]
        def decorator(func):
            return func
        return decorator

    def stop_after_attempt(*args, **kwargs):  # type: ignore[override]
        return None

    def wait_fixed(*args, **kwargs):  # type: ignore[override]
        return None


SYSTEM_PROMPT = (
    "You are a safe healthcare communication assistant. "
    "You help rewrite patient-facing explanations in simple language. "
    "Do not diagnose. "
    "Do not prescribe. "
    "Do not recommend treatment. "
    "Do not change any lab values, dates, statuses, or trends. "
    "Use only the provided structured context. "
    "Always keep the response educational and direct the patient to a healthcare provider. "
    "Return valid JSON with exactly these keys: summary, plain_language_explanation."
)


class OpenAIClient(BaseLLMClient):
    """Optional language-polishing client that targets OpenRouter."""

    def __init__(self, settings: Settings | None = None, client: Any | None = None) -> None:
        self.settings = settings or get_settings()
        if client is not None:
            self.client = client
            return

        try:
            from openai import OpenAI
        except ModuleNotFoundError as exc:  # pragma: no cover - depends on local optional install
            raise RuntimeError("openai package is required for the openrouter provider") from exc

        self.client = OpenAI(
            api_key=self.settings.openai_api_key,
            base_url=self.settings.openai_base_url,
            timeout=self.settings.llm_timeout_seconds,
        )

    def enhance_response(self, context: dict[str, Any]) -> dict[str, Any]:
        prompt = build_prompt(context)
        try:
            raw_content = self._generate_response(prompt)
        except Exception as exc:
            return {
                "summary": context.get("summary", ""),
                "plain_language_explanation": context.get("plain_language_explanation", ""),
                "llm_used": False,
                "llm_error": f"openrouter_request_failed: {exc.__class__.__name__}",
            }

        parsed = _parse_json_response(raw_content)
        if not parsed:
            return {
                "summary": context.get("summary", ""),
                "plain_language_explanation": context.get("plain_language_explanation", ""),
                "llm_used": False,
                "llm_error": "openrouter_invalid_json",
            }
        return {
            "summary": str(parsed.get("summary", "")).strip(),
            "plain_language_explanation": str(parsed.get("plain_language_explanation", "")).strip(),
            "llm_used": True,
            "llm_error": None,
        }

    @retry(stop=stop_after_attempt(2), wait=wait_fixed(1), reraise=True)
    def _generate_response(self, prompt: str) -> str:
        response = self.client.chat.completions.create(
            model=self.settings.openai_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
        )
        return response.choices[0].message.content or ""


def build_prompt(context: dict[str, Any]) -> str:
    prompt_payload = {
        "user_question": context.get("user_question", ""),
        "summary": context.get("summary", ""),
        "plain_language_explanation": context.get("plain_language_explanation", ""),
        "trend": context.get("trend", {}),
        "abnormal_results": context.get("abnormal_results", []),
        "doctor_questions": context.get("doctor_questions", []),
        "disclaimer": context.get("disclaimer", ""),
    }
    return (
        "Rewrite only the summary and plain_language_explanation for clarity.\n"
        "Keep the medical facts exactly the same.\n"
        "Do not add diagnoses, treatment, or medication advice.\n"
        "Do not change any numbers or medical values. Only improve clarity.\n"
        f"{json.dumps(prompt_payload, indent=2)}"
    )


def _parse_json_response(content: str) -> dict[str, Any]:
    if not content.strip():
        return {}
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {}
