from pydantic import ValidationError

from backend.main import DISCLAIMER_TEXT, chat, db_manager, health_check, submit_feedback
from backend.models import ChatRequest, FeedbackRequest
from data.generate_data import generate_synthetic_dataset
from data.load_data import load_data_into_database


def seed_demo_data() -> None:
    db_manager.create_tables()
    load_data_into_database(db_manager, generate_synthetic_dataset())


def test_health_endpoint_returns_ok() -> None:
    response = health_check()

    assert response["status"] == "ok"


def test_chat_endpoint_returns_trend_aware_response() -> None:
    seed_demo_data()
    request = ChatRequest(**{
        "patient_id": "demo-patient-001",
        "message": "Explain my HbA1c trend",
        "age": 42,
        "sex": "female",
        "lab_results": [],
    })
    response = chat(request)

    assert response.session_id
    assert response.patient_id == "demo-patient-001"
    assert response.response_type == "trend_analysis"
    assert "hba1c" in response.summary.lower()
    assert response.trend is not None
    assert response.trend["test_name"] == "HbA1c"
    assert response.trend["direction"] == "increasing"
    assert response.abnormal_results
    assert response.abnormal_count > 0
    assert "average blood sugar" in response.plain_language_explanation.lower()
    assert isinstance(response.doctor_questions, list)
    assert response.doctor_questions
    assert any("HbA1c" in question for question in response.doctor_questions)
    assert "not medical advice" in response.reply.lower()
    assert "not medical advice" in response.disclaimer.lower()
    assert response.safety_result.is_safe is True
    assert response.safety_status == "SAFE"
    assert response.latency_ms >= 0
    assert response.tools_used
    assert response.model_provider == "deterministic"
    assert response.model_name == "rule-based-orchestrator-v1"


def test_feedback_endpoint_accepts_placeholder_feedback() -> None:
    seed_demo_data()
    chat_response = chat(
        ChatRequest(patient_id="demo-patient-001", message="Explain my glucose result"),
    )
    feedback_request = FeedbackRequest(
        patient_id="demo-patient-001",
        session_id=chat_response.session_id,
        rating="thumbs_up",
        comment="Helpful summary",
    )

    response = submit_feedback(feedback_request)

    assert response["status"] == "accepted"
    stored_feedback = db_manager.fetch_feedback_by_session(chat_response.session_id)
    assert stored_feedback
    assert stored_feedback[-1]["rating"] == "thumbs_up"


def test_chat_request_validation_rejects_invalid_payload() -> None:
    try:
        ChatRequest(patient_id="", message="a")
        assert False, "ValidationError was expected"
    except ValidationError as exc:
        message = str(exc)

    assert "patient_id" in message
    assert "at least 2 characters" in message


def test_dummy_response_always_includes_disclaimer() -> None:
    response = chat(ChatRequest(patient_id="unknown-patient-007", message="Help"))

    assert response.disclaimer == DISCLAIMER_TEXT


def test_feedback_rating_validation_rejects_invalid_value() -> None:
    try:
        FeedbackRequest(
            patient_id="patient-001",
            session_id="session-001",
            rating="maybe",
        )
        assert False, "ValidationError was expected"
    except ValidationError as exc:
        message = str(exc)

    assert "thumbs_up" in message
    assert "thumbs_down" in message


def test_chat_endpoint_blocks_diagnosis_request_and_stores_it() -> None:
    seed_demo_data()
    response = chat(ChatRequest(patient_id="demo-patient-001", message="Do I have diabetes?"))

    assert response.safety_status == "FLAGGED"
    assert response.safety_result.is_safe is False
    assert "diagnose" in response.reply.lower()
    assert response.response_type == "safety_refusal"
    assert response.trend is None
    assert response.abnormal_results == []
    assert response.abnormal_count == 0

    stored = db_manager.fetch_interactions_by_session_id(response.session_id)
    assert stored
    assert stored[-1]["safety_triggered"] == 1


def test_chat_writes_interaction_to_sqlite() -> None:
    seed_demo_data()
    response = chat(ChatRequest(patient_id="demo-patient-001", message="Explain my HbA1c trend"))

    stored = db_manager.fetch_interactions_by_session_id(response.session_id)

    assert stored
    assert stored[-1]["patient_id"] == "demo-patient-001"
    assert "not medical advice" in stored[-1]["assistant_response"].lower()
    assert stored[-1]["model_provider"] == "deterministic"
    assert stored[-1]["model_name"] == "rule-based-orchestrator-v1"


def test_unknown_patient_returns_safe_controlled_response() -> None:
    response = chat(ChatRequest(patient_id="unknown-patient-001", message="Explain my HbA1c trend"))

    assert response.safety_status == "SAFE"
    assert response.response_type == "no_data"
    assert "no lab data was found" in response.reply.lower()
    assert response.safety_result.is_safe is True


def test_chat_reply_is_short_and_not_repetitive() -> None:
    seed_demo_data()
    response = chat(ChatRequest(patient_id="demo-patient-001", message="Explain my HbA1c trend"))

    assert len(response.reply) < 320
    assert response.reply.lower().count("hba1c") <= 3


def test_chat_response_includes_structured_json_fields() -> None:
    seed_demo_data()
    response = chat(ChatRequest(patient_id="demo-patient-001", message="Explain my HbA1c trend"))

    assert response.summary
    assert response.trend is not None
    assert isinstance(response.abnormal_results, list)
    assert response.abnormal_count >= 0
    assert response.critical_count >= 0
    assert isinstance(response.doctor_questions, list)
    assert response.disclaimer
    assert response.safety_result is not None
