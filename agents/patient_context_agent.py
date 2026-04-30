"""Deterministic patient context agent."""

from __future__ import annotations

from typing import Any

from tools.lab_tools import LabTools


class PatientContextAgent:
    """Fetch and summarize patient lab context for downstream agents."""

    def __init__(self, lab_tools: LabTools | None = None) -> None:
        self.lab_tools = lab_tools or LabTools()

    def run(self, patient_id: str) -> dict[str, Any]:
        normalized_patient_id = patient_id.strip() if patient_id else ""
        profile = self.lab_tools.database_manager.fetch_patient_profile(normalized_patient_id) or {}
        recent_lab_results = self.lab_tools.database_manager.fetch_recent_completed_lab_results(
            normalized_patient_id,
        )

        return {
            "patient_id": normalized_patient_id,
            "age": profile.get("age"),
            "sex": profile.get("sex"),
            "recent_lab_results": recent_lab_results,
        }
