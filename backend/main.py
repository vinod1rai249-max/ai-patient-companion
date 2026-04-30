"""FastAPI application entrypoint."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from agents.orchestrator import Orchestrator
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from backend.config import get_settings
from backend.database import DatabaseManager
from backend.logging_config import configure_logging
from backend.models import (
    ChatRequest,
    ChatResponse,
    ErrorResponse,
    FeedbackRequest,
    SafetyResult,
)

DISCLAIMER_TEXT = (
    "This information is for education only and is not medical advice. "
    "Please review your lab results and any concerns with your healthcare provider."
)
TOOLS_USED = [
    "PatientContextAgent",
    "TrendAnalysisAgent",
    "ExplanationAgent",
    "DoctorQuestionAgent",
    "SafetyGuardrailAgent",
    "LabTools",
    "SafetyTools",
]
BLOCKED_TOOLS_USED = ["SafetyGuardrailAgent", "SafetyTools"]

settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger(__name__)
db_manager = DatabaseManager(settings.database_url)
orchestrator = Orchestrator()


@asynccontextmanager
async def lifespan(_: FastAPI):
    db_manager.create_tables()
    logger.info("Application startup completed")
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)


def build_error_response(
    error: str,
    message: str,
    status_code: int,
    details: dict | None = None,
) -> JSONResponse:
    payload = ErrorResponse(
        error=error,
        message=message,
        details=details,
    )
    return JSONResponse(status_code=status_code, content=payload.model_dump())


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    _: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    return build_error_response(
        error="validation_error",
        message="Request validation failed",
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        details={"issues": exc.errors()},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
    detail_message = exc.detail if isinstance(exc.detail, str) else "HTTP error"
    detail_payload = exc.detail if isinstance(exc.detail, dict) else None
    return build_error_response(
        error="http_error",
        message=detail_message,
        status_code=exc.status_code,
        details=detail_payload,
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled server error: %s", exc)
    return build_error_response(
        error="internal_server_error",
        message="An unexpected error occurred",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "app_name": settings.app_name, "env": settings.env}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    db_manager.upsert_patient(request.patient_id, request.age, request.sex)
    orchestrated = orchestrator.run(request)
    session_id = orchestrated["session_id"]
    db_manager.create_chat_session(session_id, request.patient_id)

    safety_triggers = orchestrated["safety"]["triggers"]
    logger.info(
        "chat_completed provider=%s model=%s llm_used=%s llm_error=%s safety_triggered=%s latency_ms=%s",
        orchestrated.get("model_provider", "deterministic"),
        orchestrated.get("model_name", "rule-based-orchestrator-v1"),
        orchestrated.get("llm_used", False),
        orchestrated.get("llm_error"),
        orchestrated.get("safety_triggered", False),
        orchestrated["latency_ms"],
    )
    db_manager.insert_interaction(
        session_id=session_id,
        patient_id=request.patient_id,
        user_message=request.message,
        assistant_response=orchestrated["reply"],
        latency_ms=float(orchestrated["latency_ms"]),
        safety_triggered=bool(orchestrated.get("safety_triggered", False) or not orchestrated["safety"]["is_safe"]),
        model_provider=orchestrated.get("model_provider", "deterministic"),
        model_name=orchestrated.get("model_name", "rule-based-orchestrator-v1"),
        safety_triggers=",".join(safety_triggers),
        response_quality="openrouter_enhanced" if orchestrated.get("llm_used") else "deterministic_orchestrated_response",
    )

    return ChatResponse(
        session_id=session_id,
        patient_id=request.patient_id,
        response_type=orchestrated["response_type"],
        summary=orchestrated["summary"],
        trend=orchestrated["trend"],
        abnormal_results=orchestrated["abnormal_results"],
        abnormal_count=int(orchestrated["abnormal_count"]),
        critical_count=int(orchestrated["critical_count"]),
        plain_language_explanation=orchestrated["plain_language_explanation"],
        doctor_questions=orchestrated["doctor_questions"],
        reply=orchestrated["reply"],
        disclaimer=orchestrated["disclaimer"],
        safety_result=SafetyResult(**orchestrated["safety"]),
        safety_status=orchestrated["safety_status"],
        latency_ms=float(orchestrated["latency_ms"]),
        tools_used=BLOCKED_TOOLS_USED if orchestrated["safety_status"] == "FLAGGED" else TOOLS_USED,
        model_provider=orchestrated.get("model_provider", "deterministic"),
        model_name=orchestrated.get("model_name", "rule-based-orchestrator-v1"),
        feedback_enabled=True,
    )


@app.post("/feedback")
def submit_feedback(request: FeedbackRequest) -> dict[str, str]:
    db_manager.upsert_patient(request.patient_id, age=None, sex=None)
    db_manager.create_chat_session(request.session_id, request.patient_id)
    db_manager.save_feedback(
        session_id=request.session_id,
        patient_id=request.patient_id,
        rating=request.rating.value,
        comment=request.comment,
    )
    return {"status": "accepted", "message": "Feedback recorded"}
