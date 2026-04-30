"""Pydantic models for API contracts and validation."""

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class LabStatus(str, Enum):
    NORMAL = "NORMAL"
    LOW = "LOW"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class FeedbackRating(str, Enum):
    THUMBS_UP = "thumbs_up"
    THUMBS_DOWN = "thumbs_down"


class Patient(BaseModel):
    patient_id: str = Field(..., min_length=1)
    age: int | None = Field(default=None, ge=0, le=120)
    sex: str | None = Field(default=None, min_length=1, max_length=20)

    @field_validator("patient_id")
    @classmethod
    def validate_patient_id(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("patient_id is required")
        return stripped


class LabResult(BaseModel):
    patient_id: str = Field(..., min_length=1)
    test_name: str = Field(..., min_length=1)
    value: float
    unit: str | None = None
    normal_range: str = Field(..., min_length=1)
    status: LabStatus
    collected_at: datetime | None = None


class ChatRequest(BaseModel):
    patient_id: str = Field(..., min_length=1)
    message: str = Field(..., min_length=2)
    age: int | None = Field(default=None, ge=0, le=120)
    sex: str | None = Field(default=None, min_length=1, max_length=20)
    session_id: str | None = None
    lab_results: list[LabResult] = Field(default_factory=list)

    @field_validator("patient_id")
    @classmethod
    def validate_chat_patient_id(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("patient_id is required")
        return stripped

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        stripped = value.strip()
        if len(stripped) < 2:
            raise ValueError("message must be at least 2 characters long")
        return stripped


class SafetyResult(BaseModel):
    is_safe: bool
    triggers: list[str] = Field(default_factory=list)
    disclaimer_added: bool = True


class ChatResponse(BaseModel):
    session_id: str
    patient_id: str
    response_type: str
    summary: str
    trend: dict[str, Any] | None = None
    abnormal_results: list[dict[str, Any]] = Field(default_factory=list)
    abnormal_count: int = 0
    critical_count: int = 0
    plain_language_explanation: str
    doctor_questions: list[str] = Field(default_factory=list)
    reply: str
    disclaimer: str
    safety_result: SafetyResult
    safety_status: Literal["SAFE", "FLAGGED"]
    latency_ms: float = Field(..., ge=0)
    tools_used: list[str] = Field(default_factory=list)
    model_provider: str
    model_name: str
    feedback_enabled: bool = True


class FeedbackRequest(BaseModel):
    patient_id: str = Field(..., min_length=1)
    session_id: str = Field(..., min_length=1)
    rating: FeedbackRating
    comment: str | None = Field(default=None, max_length=1000)

    @field_validator("patient_id", "session_id")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("field is required")
        return stripped


class TrendResult(BaseModel):
    patient_id: str = Field(..., min_length=1)
    test_name: str = Field(..., min_length=1)
    direction: str = Field(..., min_length=1)
    summary: str = Field(..., min_length=1)
    points_analyzed: int = Field(..., ge=0)


class ErrorResponse(BaseModel):
    error: str
    message: str
    details: dict[str, Any] | None = None
