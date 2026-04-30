"""Deterministic multi-agent orchestrator with no LLM dependency."""

from __future__ import annotations

from time import perf_counter
from typing import Any
from uuid import uuid4

from agents.doctor_question_agent import DoctorQuestionAgent
from agents.explanation_agent import ExplanationAgent
from agents.patient_context_agent import PatientContextAgent
from agents.safety_guardrail_agent import SafetyGuardrailAgent
from agents.trend_analysis_agent import TrendAnalysisAgent
from backend.config import Settings, get_settings
from backend.models import ChatRequest
from llm.base import BaseLLMClient
from llm.openai_client import OpenAIClient
from tools.lab_tools import LabTools
from tools.safety_tools import PROVIDER_DISCLAIMER


class Orchestrator:
    """Coordinate deterministic agents into one structured response."""

    def __init__(
        self,
        patient_context_agent: PatientContextAgent | None = None,
        trend_analysis_agent: TrendAnalysisAgent | None = None,
        explanation_agent: ExplanationAgent | None = None,
        doctor_question_agent: DoctorQuestionAgent | None = None,
        safety_guardrail_agent: SafetyGuardrailAgent | None = None,
        settings: Settings | None = None,
        llm_client: BaseLLMClient | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.patient_context_agent = patient_context_agent or PatientContextAgent()
        self.trend_analysis_agent = trend_analysis_agent or TrendAnalysisAgent()
        self.explanation_agent = explanation_agent or ExplanationAgent()
        self.doctor_question_agent = doctor_question_agent or DoctorQuestionAgent()
        self.safety_guardrail_agent = safety_guardrail_agent or SafetyGuardrailAgent()
        self.lab_tools = LabTools()
        self.llm_client = llm_client or self._build_llm_client()

    def run(self, request: ChatRequest) -> dict[str, Any]:
        start_time = perf_counter()
        session_id = request.session_id or str(uuid4())

        user_safety = self.safety_guardrail_agent.validate_user_message(request.message)
        if not user_safety["allow"]:
            blocked = self.safety_guardrail_agent.build_blocked_response(user_safety)
            blocked.update(
                {
                    "patient_id": request.patient_id,
                    "response_type": "safety_refusal",
                    "summary": blocked["reply"],
                    "trend": None,
                    "abnormal_results": [],
                    "abnormal_count": 0,
                    "critical_count": 0,
                    "plain_language_explanation": "I can help explain completed lab results, but I cannot diagnose or prescribe.",
                    "doctor_questions": [],
                    "session_id": session_id,
                    "latency_ms": round((perf_counter() - start_time) * 1000, 2),
                    "feedback_enabled": True,
                    "model_provider": "deterministic",
                    "model_name": "rule-based-orchestrator-v1",
                    "llm_used": False,
                    "llm_error": None,
                    "safety_triggered": True,
                    "patient_context": {},
                    "trend_analysis": {"trends": [], "trend_summaries": []},
                    "explanations": {},
                    "doctor_questions_full": [],
                }
            )
            return blocked

        patient_context = self.patient_context_agent.run(request.patient_id)
        recent_lab_results = patient_context["recent_lab_results"]
        abnormal_results = self.lab_tools.get_abnormal_results_from_scoped_context(recent_lab_results)
        abnormal_count = len(abnormal_results)
        critical_count = sum(1 for result in abnormal_results if result["status"] == "CRITICAL")
        test_names = self._prioritize_test_names(
            available_tests=sorted({result["test_name"] for result in recent_lab_results}),
            message=request.message,
        )
        trend_analysis = self.trend_analysis_agent.run(
            request.patient_id,
            test_names,
            lab_results=recent_lab_results,
        )
        explanations = self.explanation_agent.run(test_names)
        doctor_questions = self.doctor_question_agent.run(trend_analysis["trends"])
        primary_trend = self._pick_primary_trend(trend_analysis["trends"])
        summary = self._build_summary(request.patient_id, primary_trend, abnormal_results)
        plain_language_explanation = self._build_explanation_text(
            primary_trend=primary_trend,
            explanations=explanations["explanations"],
        )
        selected_questions = self._prioritize_doctor_questions(
            abnormal_results=abnormal_results,
            doctor_questions=doctor_questions["doctor_questions"],
        )[:3]
        llm_result = self._apply_optional_llm_polish(
            request=request,
            summary=summary,
            plain_language_explanation=plain_language_explanation,
            trend=self._shape_trend(primary_trend),
            abnormal_results=abnormal_results,
            doctor_questions=selected_questions,
        )
        summary = llm_result["summary"]
        plain_language_explanation = llm_result["plain_language_explanation"]
        reply = self._build_reply(
            summary=summary,
            doctor_questions=selected_questions,
        )

        final_response_text = f"{reply} {PROVIDER_DISCLAIMER}"
        final_safety = self.safety_guardrail_agent.validate_final_response(final_response_text)

        return {
            "session_id": session_id,
            "patient_id": request.patient_id,
            "response_type": "trend_analysis" if primary_trend else "no_data",
            "summary": summary,
            "trend": self._shape_trend(primary_trend),
            "abnormal_results": abnormal_results,
            "abnormal_count": abnormal_count,
            "critical_count": critical_count,
            "plain_language_explanation": plain_language_explanation,
            "doctor_questions": selected_questions,
            "reply": final_response_text,
            "disclaimer": PROVIDER_DISCLAIMER,
            "safety": {
                "is_safe": final_safety["is_valid"],
                "triggers": final_safety["triggers"],
                "disclaimer_added": True,
            },
            "safety_status": "SAFE" if final_safety["is_valid"] else "FLAGGED",
            "latency_ms": round((perf_counter() - start_time) * 1000, 2),
            "feedback_enabled": True,
            "model_provider": llm_result["model_provider"],
            "model_name": llm_result["model_name"],
            "llm_used": llm_result["llm_used"],
            "llm_error": llm_result["llm_error"],
            "safety_triggered": llm_result["safety_triggered"] or not final_safety["is_valid"],
            "patient_context": patient_context,
            "trend_analysis": trend_analysis,
            "explanations": explanations["explanations"],
            "doctor_questions_full": doctor_questions["doctor_questions"],
        }

    def _build_llm_client(self) -> BaseLLMClient | None:
        if self.settings.llm_provider != "openrouter":
            return None
        if not self.settings.openai_api_key.strip():
            return None
        return OpenAIClient(settings=self.settings)

    def _apply_optional_llm_polish(
        self,
        request: ChatRequest,
        summary: str,
        plain_language_explanation: str,
        trend: dict[str, Any] | None,
        abnormal_results: list[dict[str, Any]],
        doctor_questions: list[str],
    ) -> dict[str, Any]:
        if self.llm_client is None:
            provider = "deterministic"
            llm_error = None
            if self.settings.llm_provider == "openrouter":
                provider = "deterministic_fallback"
                llm_error = "openrouter_unavailable"
            return {
                "summary": summary,
                "plain_language_explanation": plain_language_explanation,
                "model_provider": provider,
                "model_name": "rule-based-orchestrator-v1",
                "llm_used": False,
                "llm_error": llm_error,
                "safety_triggered": False,
            }

        rewritten = self.llm_client.enhance_response(
            {
                "user_question": request.message,
                "summary": summary,
                "plain_language_explanation": plain_language_explanation,
                "trend": trend or {},
                "abnormal_results": abnormal_results,
                "doctor_questions": doctor_questions,
                "disclaimer": PROVIDER_DISCLAIMER,
            }
        )

        llm_used = bool(rewritten.get("llm_used"))
        llm_error = rewritten.get("llm_error")
        candidate_summary = rewritten.get("summary") or summary
        candidate_explanation = rewritten.get("plain_language_explanation") or plain_language_explanation
        safety_triggered = False

        raw_validation_target = f"{candidate_summary} {candidate_explanation} {PROVIDER_DISCLAIMER}"
        raw_safety = self.safety_guardrail_agent.validate_final_response(raw_validation_target)
        if not raw_safety["is_valid"]:
            return {
                "summary": summary,
                "plain_language_explanation": plain_language_explanation,
                "model_provider": "deterministic_fallback",
                "model_name": "rule-based-orchestrator-v1",
                "llm_used": False,
                "llm_error": llm_error or "unsafe_llm_output_blocked",
                "safety_triggered": True,
            }

        if not self._preserves_deterministic_facts(summary, candidate_summary):
            candidate_summary = summary
            llm_used = False
            llm_error = llm_error or "numeric_or_fact_change_blocked"
        if not self._preserves_deterministic_facts(plain_language_explanation, candidate_explanation):
            candidate_explanation = plain_language_explanation
            llm_used = False
            llm_error = llm_error or "numeric_or_fact_change_blocked"

        provider = "openrouter" if llm_used else "deterministic_fallback"
        model_name = self.settings.openai_model if llm_used else "rule-based-orchestrator-v1"

        return {
            "summary": candidate_summary,
            "plain_language_explanation": candidate_explanation,
            "model_provider": provider,
            "model_name": model_name,
            "llm_used": llm_used,
            "llm_error": llm_error,
            "safety_triggered": safety_triggered,
        }

    @staticmethod
    def _preserves_deterministic_facts(source_text: str, candidate_text: str) -> bool:
        source_numbers = Orchestrator._extract_numeric_tokens(source_text)
        candidate_numbers = Orchestrator._extract_numeric_tokens(candidate_text)
        if source_numbers != candidate_numbers:
            return False

        protected_terms = ["HIGH", "LOW", "CRITICAL", "increasing", "decreasing", "stable"]
        for term in protected_terms:
            if term.lower() in source_text.lower() and term.lower() not in candidate_text.lower():
                return False
        return True

    @staticmethod
    def _extract_numeric_tokens(text: str) -> list[str]:
        token = ""
        tokens: list[str] = []
        for char in text:
            if char.isdigit() or char == ".":
                token += char
            elif token:
                tokens.append(token)
                token = ""
        if token:
            tokens.append(token)
        return tokens

    def _current_model_name(self) -> str:
        if self.settings.llm_provider == "openrouter" and self.llm_client is not None:
            return self.settings.openai_model
        return "rule-based-orchestrator-v1"

    def _current_model_provider(self) -> str:
        if self.settings.llm_provider == "openrouter" and self.llm_client is not None:
            return "openrouter"
        return "deterministic"

    @staticmethod
    def _build_reply(
        summary: str,
        doctor_questions: list[str],
    ) -> str:
        if doctor_questions:
            return f"{summary} Consider asking: {doctor_questions[0]}"
        return summary

    @staticmethod
    def _prioritize_test_names(available_tests: list[str], message: str) -> list[str]:
        normalized_message = message.lower()
        mentioned = [
            test_name for test_name in available_tests if test_name.lower() in normalized_message
        ]
        remaining = [test_name for test_name in available_tests if test_name not in mentioned]
        return mentioned + remaining

    @staticmethod
    def _pick_primary_trend(trends: list[dict[str, Any]]) -> dict[str, Any] | None:
        meaningful_trends = [trend for trend in trends if trend.get("total_results", 0) > 0]
        return meaningful_trends[0] if meaningful_trends else None

    @staticmethod
    def _prioritize_doctor_questions(
        abnormal_results: list[dict[str, Any]],
        doctor_questions: list[str],
    ) -> list[str]:
        if not abnormal_results:
            return doctor_questions

        abnormal_test_names = {str(result.get("test_name", "")).lower() for result in abnormal_results}
        prioritized: list[str] = []
        remaining: list[str] = []

        for question in doctor_questions:
            normalized_question = question.lower()
            if any(test_name and test_name in normalized_question for test_name in abnormal_test_names):
                prioritized.append(question)
            else:
                remaining.append(question)

        return prioritized + remaining

    @staticmethod
    def _shape_trend(trend: dict[str, Any] | None) -> dict[str, Any] | None:
        if not trend:
            return None
        return {
            "test_name": trend.get("test_name"),
            "direction": trend.get("direction"),
            "pattern_summary": trend.get("pattern_summary"),
            "risk_signal": trend.get("risk_signal"),
            "first_value": trend.get("first_value"),
            "latest_value": trend.get("latest_value"),
            "absolute_change": trend.get("absolute_change"),
            "percent_change": trend.get("percent_change"),
            "latest_status": trend.get("latest_status"),
        }

    @staticmethod
    def _build_summary(
        patient_id: str,
        trend: dict[str, Any] | None,
        abnormal_results: list[dict[str, Any]],
    ) -> str:
        if abnormal_results:
            primary_abnormal = abnormal_results[0]
            if trend and trend.get("pattern_summary") in {"consistent increase", "consistent decrease"}:
                pattern_phrase = "consistently increased"
                if trend["pattern_summary"] == "consistent decrease":
                    pattern_phrase = "consistently decreased"
                return (
                    f"Over the past 5 years, your {trend['test_name']} has {pattern_phrase} "
                    f"and is now in the {trend['latest_status']} range."
                )
            return (
                f"Your latest out-of-range result is {primary_abnormal['test_name']} "
                f"with a {primary_abnormal['status']} status."
            )
        if not trend:
            return f"No lab data was found for patient '{patient_id}'."
        return f"Your {trend['test_name']} trend is {trend['direction']}."

    @staticmethod
    def _build_explanation_text(
        primary_trend: dict[str, Any] | None,
        explanations: dict[str, str],
    ) -> str:
        if not primary_trend:
            return "No lab explanation is available because no matching lab data was found."
        test_name = str(primary_trend["test_name"])
        return explanations.get(
            test_name,
            "A plain-language explanation is not available yet for this test.",
        )
