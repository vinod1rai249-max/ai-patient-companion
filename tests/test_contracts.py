from backend.config import get_settings
from backend.models import ChatResponse, FeedbackRequest, SafetyResult


def test_settings_default_contract() -> None:
    settings = get_settings()

    assert settings.app_name == "AI Companion for Patients"
    assert settings.env == "local"
    assert settings.database_url == "sqlite:///./data/ai_patient_companion.db"
    assert settings.llm_provider in {"deterministic", "openrouter"}
    assert settings.openai_model
    assert settings.openai_base_url == "https://openrouter.ai/api/v1"
    assert settings.llm_timeout_seconds == 30
    assert settings.log_level == "INFO"


def test_chat_response_contract_fields() -> None:
    response = ChatResponse(
        session_id="session-001",
        patient_id="patient-001",
        response_type="trend_analysis",
        summary="Your HbA1c trend is increasing.",
        abnormal_results=[
            {
                "test_name": "HbA1c",
                "date": "2026-06-15",
                "value": 7.0,
                "unit": "%",
                "normal_range": "4.0-5.6",
                "status": "HIGH",
                "trend_direction": "increasing",
            }
        ],
        abnormal_count=1,
        critical_count=0,
        trend={
            "test_name": "HbA1c",
            "direction": "increasing",
            "first_value": 5.6,
            "latest_value": 7.0,
            "absolute_change": 1.4,
            "percent_change": 25.0,
            "latest_status": "HIGH",
        },
        plain_language_explanation="HbA1c reflects average blood sugar over the past two to three months.",
        doctor_questions=["What could be contributing to my HbA1c increase?"],
        reply="Safe placeholder response",
        disclaimer="Please review with your healthcare provider.",
        safety_result=SafetyResult(is_safe=True),
        safety_status="SAFE",
        latency_ms=12.5,
        tools_used=["LabTools"],
        model_provider="deterministic",
        model_name="rule-based-orchestrator-v1",
        feedback_enabled=True,
    )

    payload = response.model_dump()

    assert set(payload) == {
        "session_id",
        "patient_id",
        "response_type",
        "summary",
        "trend",
        "abnormal_results",
        "abnormal_count",
        "critical_count",
        "plain_language_explanation",
        "doctor_questions",
        "reply",
        "disclaimer",
        "safety_result",
        "safety_status",
        "latency_ms",
        "tools_used",
        "model_provider",
        "model_name",
        "feedback_enabled",
    }
    assert set(payload["safety_result"]) == {"is_safe", "triggers", "disclaimer_added"}
    assert payload["trend"]["test_name"] == "HbA1c"
    assert payload["abnormal_results"][0]["status"] == "HIGH"


def test_feedback_request_contract_accepts_allowed_ratings() -> None:
    request = FeedbackRequest(
        patient_id="patient-001",
        session_id="session-001",
        rating="thumbs_down",
        comment="Not clear enough",
    )

    assert request.rating.value == "thumbs_down"
