from agents.doctor_question_agent import DoctorQuestionAgent
from agents.explanation_agent import ExplanationAgent
from agents.orchestrator import Orchestrator
from agents.patient_context_agent import PatientContextAgent
from agents.safety_guardrail_agent import SafetyGuardrailAgent
from agents.trend_analysis_agent import TrendAnalysisAgent
from backend.config import Settings
from backend.database import DatabaseManager
from backend.models import ChatRequest
from data.generate_data import generate_synthetic_dataset
from data.load_data import load_data_into_database
from tests.test_data_pipeline import make_database_url, make_scratch_path
from tools.lab_tools import LabTools


class FakeLLMClient:
    def __init__(self, summary: str, explanation: str) -> None:
        self.summary = summary
        self.explanation = explanation

    def enhance_response(self, context: dict[str, str]) -> dict[str, str | bool | None]:
        return {
            "summary": self.summary,
            "plain_language_explanation": self.explanation,
            "llm_used": True,
            "llm_error": None,
        }


class FailingLLMClient:
    def enhance_response(self, context: dict[str, str]) -> dict[str, str | bool | None]:
        return {
            "summary": context["summary"],
            "plain_language_explanation": context["plain_language_explanation"],
            "llm_used": False,
            "llm_error": "openrouter_request_failed: TimeoutError",
        }


def build_agent_stack() -> tuple[
    PatientContextAgent,
    TrendAnalysisAgent,
    ExplanationAgent,
    DoctorQuestionAgent,
    SafetyGuardrailAgent,
    Orchestrator,
]:
    database_manager = DatabaseManager(make_database_url(make_scratch_path("agents.db")))
    database_manager.create_tables()
    load_data_into_database(database_manager, generate_synthetic_dataset())
    lab_tools = LabTools(database_manager=database_manager)

    patient_context_agent = PatientContextAgent(lab_tools=lab_tools)
    trend_analysis_agent = TrendAnalysisAgent(lab_tools=lab_tools)
    explanation_agent = ExplanationAgent()
    doctor_question_agent = DoctorQuestionAgent()
    safety_guardrail_agent = SafetyGuardrailAgent()
    orchestrator = Orchestrator(
        patient_context_agent=patient_context_agent,
        trend_analysis_agent=trend_analysis_agent,
        explanation_agent=explanation_agent,
        doctor_question_agent=doctor_question_agent,
        safety_guardrail_agent=safety_guardrail_agent,
    )
    return (
        patient_context_agent,
        trend_analysis_agent,
        explanation_agent,
        doctor_question_agent,
        safety_guardrail_agent,
        orchestrator,
    )


def make_openrouter_settings() -> Settings:
    return Settings(
        llm_provider="openrouter",
        openai_api_key="test-key",
        openai_model="openai/gpt-4o-mini",
        openai_base_url="https://openrouter.ai/api/v1",
        llm_timeout_seconds=30,
    )


def test_patient_context_agent_returns_structured_context() -> None:
    patient_context_agent, _, _, _, _, _ = build_agent_stack()

    result = patient_context_agent.run("demo-patient-001")

    assert result["patient_id"] == "demo-patient-001"
    assert result["age"] == 52
    assert result["sex"] == "female"
    assert len(result["recent_lab_results"]) <= 20
    assert "name" not in result
    assert "insurance" not in result
    assert "provider" not in result
    assert "medication" not in result
    assert "diagnosis" not in result
    assert "procedure" not in result


def test_trend_analysis_agent_returns_trend_summaries() -> None:
    patient_context_agent, trend_analysis_agent, _, _, _, _ = build_agent_stack()
    context = patient_context_agent.run("demo-patient-001")

    result = trend_analysis_agent.run(
        "demo-patient-001",
        ["HbA1c", "Total Cholesterol"],
        lab_results=context["recent_lab_results"],
    )

    assert len(result["trends"]) == 2
    assert any("increasing" in summary for summary in result["trend_summaries"])
    assert context["recent_lab_results"]


def test_explanation_agent_returns_static_definitions() -> None:
    _, _, explanation_agent, _, _, _ = build_agent_stack()

    result = explanation_agent.run(["HbA1c", "LDL"])

    assert "average blood sugar" in result["explanations"]["HbA1c"]
    assert "bad cholesterol" in result["explanations"]["LDL"]


def test_doctor_question_agent_generates_rule_based_questions() -> None:
    _, trend_analysis_agent, _, doctor_question_agent, _, _ = build_agent_stack()
    trend_result = trend_analysis_agent.run("demo-patient-001", ["HbA1c"])

    result = doctor_question_agent.run(trend_result["trends"])

    assert result["doctor_questions"]
    assert any("HbA1c" in question for question in result["doctor_questions"])


def test_safety_guardrail_agent_blocks_unsafe_message() -> None:
    _, _, _, _, safety_guardrail_agent, _ = build_agent_stack()

    validation = safety_guardrail_agent.validate_user_message("Do I have diabetes?")
    blocked = safety_guardrail_agent.build_blocked_response(validation)

    assert validation["allow"] is False
    assert blocked["safety_status"] == "FLAGGED"


def test_orchestrator_returns_structured_response_for_safe_request() -> None:
    _, _, _, _, _, orchestrator = build_agent_stack()

    result = orchestrator.run(
        ChatRequest(
            patient_id="demo-patient-001",
            message="Explain my HbA1c and cholesterol trends",
        )
    )

    assert result["session_id"]
    assert result["safety_status"] == "SAFE"
    assert result["abnormal_results"]
    assert result["abnormal_count"] > 0
    assert "out-of-range" in result["summary"].lower() or "past 5 years" in result["summary"].lower()
    assert result["trend_analysis"]["trends"]
    assert result["doctor_questions"]
    assert any(
        abnormal_result["test_name"] in question
        for abnormal_result in result["abnormal_results"]
        for question in result["doctor_questions"]
    )


def test_patient_context_agent_uses_recent_completed_results_only() -> None:
    patient_context_agent, _, _, _, _, _ = build_agent_stack()

    result = patient_context_agent.run("demo-patient-001")

    assert len(result["recent_lab_results"]) <= 20
    assert all(result_item["collected_at"] is not None for result_item in result["recent_lab_results"])


def test_orchestrator_blocks_unsafe_request_before_other_agents() -> None:
    _, _, _, _, _, orchestrator = build_agent_stack()

    result = orchestrator.run(
        ChatRequest(
            patient_id="demo-patient-001",
            message="Should I take metformin?",
        )
    )

    assert result["safety_status"] == "FLAGGED"
    assert result["trend_analysis"]["trends"] == []
    assert result["doctor_questions"] == []
    assert result["abnormal_results"] == []


def test_orchestrator_uses_openrouter_polish_without_changing_structure() -> None:
    patient_context_agent, trend_analysis_agent, explanation_agent, doctor_question_agent, safety_guardrail_agent, _ = build_agent_stack()
    orchestrator = Orchestrator(
        patient_context_agent=patient_context_agent,
        trend_analysis_agent=trend_analysis_agent,
        explanation_agent=explanation_agent,
        doctor_question_agent=doctor_question_agent,
        safety_guardrail_agent=safety_guardrail_agent,
        settings=make_openrouter_settings(),
        llm_client=FakeLLMClient(
            summary="Over the past 5 years, your HbA1c has consistently increased and is now in the HIGH range.",
            explanation="HbA1c reflects your average blood sugar over the past two to three months.",
        ),
    )

    result = orchestrator.run(
        ChatRequest(patient_id="demo-patient-001", message="Explain my HbA1c trend")
    )

    assert result["model_provider"] == "openrouter"
    assert result["model_name"] == "openai/gpt-4o-mini"
    assert result["llm_used"] is True
    assert result["llm_error"] is None
    assert result["summary"].startswith("Over the past 5 years")
    assert result["trend"]["latest_value"] == 7.0
    assert result["abnormal_results"]
    assert result["doctor_questions"]


def test_orchestrator_rejects_llm_number_changes() -> None:
    patient_context_agent, trend_analysis_agent, explanation_agent, doctor_question_agent, safety_guardrail_agent, _ = build_agent_stack()
    orchestrator = Orchestrator(
        patient_context_agent=patient_context_agent,
        trend_analysis_agent=trend_analysis_agent,
        explanation_agent=explanation_agent,
        doctor_question_agent=doctor_question_agent,
        safety_guardrail_agent=safety_guardrail_agent,
        settings=make_openrouter_settings(),
        llm_client=FakeLLMClient(
            summary="Over the past 10 years, your HbA1c has consistently increased and is now in the HIGH range.",
            explanation="HbA1c reflects your average blood sugar over the past 6 months.",
        ),
    )

    result = orchestrator.run(
        ChatRequest(patient_id="demo-patient-001", message="Explain my HbA1c trend")
    )

    assert "5 years" in result["summary"]
    assert "two to three months" in result["plain_language_explanation"].lower()
    assert result["model_provider"] == "deterministic_fallback"
    assert result["llm_used"] is False


def test_orchestrator_rejects_unsafe_llm_response() -> None:
    patient_context_agent, trend_analysis_agent, explanation_agent, doctor_question_agent, safety_guardrail_agent, _ = build_agent_stack()
    orchestrator = Orchestrator(
        patient_context_agent=patient_context_agent,
        trend_analysis_agent=trend_analysis_agent,
        explanation_agent=explanation_agent,
        doctor_question_agent=doctor_question_agent,
        safety_guardrail_agent=safety_guardrail_agent,
        settings=make_openrouter_settings(),
        llm_client=FakeLLMClient(
            summary="You have diabetes and should take metformin.",
            explanation="This is definitely an emergency.",
        ),
    )

    result = orchestrator.run(
        ChatRequest(patient_id="demo-patient-001", message="Explain my HbA1c trend")
    )

    assert "you have diabetes" not in result["summary"].lower()
    assert "definitely an emergency" not in result["plain_language_explanation"].lower()
    assert result["safety_status"] == "SAFE"
    assert result["safety_triggered"] is True
    assert result["model_provider"] == "deterministic_fallback"


def test_orchestrator_falls_back_when_openrouter_fails() -> None:
    patient_context_agent, trend_analysis_agent, explanation_agent, doctor_question_agent, safety_guardrail_agent, _ = build_agent_stack()
    orchestrator = Orchestrator(
        patient_context_agent=patient_context_agent,
        trend_analysis_agent=trend_analysis_agent,
        explanation_agent=explanation_agent,
        doctor_question_agent=doctor_question_agent,
        safety_guardrail_agent=safety_guardrail_agent,
        settings=make_openrouter_settings(),
        llm_client=FailingLLMClient(),
    )

    result = orchestrator.run(
        ChatRequest(patient_id="demo-patient-001", message="Explain my HbA1c trend")
    )

    assert result["model_provider"] == "deterministic_fallback"
    assert result["model_name"] == "rule-based-orchestrator-v1"
    assert result["llm_used"] is False
    assert result["llm_error"] == "openrouter_request_failed: TimeoutError"
    assert "5 years" in result["summary"]
