"""Deterministic trend analysis agent."""

from __future__ import annotations

from typing import Any

from tools.lab_tools import LabTools


class TrendAnalysisAgent:
    """Calculate lab trends using deterministic tool functions."""

    def __init__(self, lab_tools: LabTools | None = None) -> None:
        self.lab_tools = lab_tools or LabTools()

    def run(
        self,
        patient_id: str,
        test_names: list[str],
        lab_results: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        if lab_results is None:
            trends = [
                self.lab_tools.calculate_lab_trend(patient_id=patient_id, test_name=test_name)
                for test_name in test_names
            ]
        else:
            trends = [
                self.lab_tools.calculate_lab_trend_from_results(
                    patient_id=patient_id,
                    test_name=test_name,
                    lab_results=lab_results,
                )
                for test_name in test_names
            ]
        enriched_trends = [self._add_risk_signal(trend) for trend in trends]
        return {
            "patient_id": patient_id.strip() if patient_id else "",
            "trends": enriched_trends,
            "trend_summaries": [trend["trend_summary"] for trend in enriched_trends if trend["total_results"] > 0],
        }

    @staticmethod
    def _add_risk_signal(trend: dict[str, Any]) -> dict[str, Any]:
        risk_signal = "low"
        if trend.get("critical_count", 0) > 0:
            risk_signal = "high"
        elif trend.get("abnormal_count", 0) >= 3 and trend.get("direction") == "increasing":
            risk_signal = "high"
        elif trend.get("abnormal_count", 0) >= 2 or trend.get("latest_status") in {"HIGH", "LOW"}:
            risk_signal = "moderate"

        if trend.get("pattern_summary") == "consistent increase" and trend.get("latest_status") in {"HIGH", "CRITICAL"}:
            risk_signal = "high"

        enriched = dict(trend)
        enriched["risk_signal"] = risk_signal
        return enriched
