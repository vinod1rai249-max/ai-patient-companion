"""Deterministic lab data access and trend analysis tools."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from backend.config import get_settings
from backend.database import DatabaseManager


ABNORMAL_STATUSES = {"HIGH", "LOW", "CRITICAL"}


class LabTools:
    """Reusable lab data tools for deterministic analysis before LLM use."""

    def __init__(self, database_manager: DatabaseManager | None = None) -> None:
        if database_manager is None:
            settings = get_settings()
            database_manager = DatabaseManager(settings.database_url)
        self.database_manager = database_manager

    def get_patient_lab_results(self, patient_id: str) -> list[dict[str, Any]]:
        """Return all lab results for a patient sorted by date."""

        if not patient_id or not patient_id.strip():
            return []
        return self.database_manager.fetch_lab_results_by_patient_id(patient_id.strip())

    def get_lab_results_by_test(self, patient_id: str, test_name: str) -> list[dict[str, Any]]:
        """Return all lab results for one patient and one test."""

        if not patient_id or not patient_id.strip():
            return []
        if not test_name or not test_name.strip():
            return []
        return self.database_manager.fetch_lab_results_by_patient_id_and_test_name(
            patient_id=patient_id.strip(),
            test_name=test_name.strip(),
        )

    def get_lab_time_series(self, patient_id: str, test_name: str) -> list[dict[str, Any]]:
        """Return a simple sorted time series for one patient's test."""

        results = self.get_lab_results_by_test(patient_id=patient_id, test_name=test_name)
        return sorted(results, key=lambda result: self._parse_date(result.get("collected_at")))

    @staticmethod
    def classify_trend_direction(
        first_value: float,
        latest_value: float,
        threshold_percent: float = 5.0,
    ) -> str:
        """Classify trend direction based on percentage change."""

        if first_value == 0:
            if latest_value == 0:
                return "stable"
            return "increasing" if latest_value > 0 else "decreasing"

        percent_change = ((latest_value - first_value) / abs(first_value)) * 100
        if abs(percent_change) <= threshold_percent:
            return "stable"
        if percent_change > 0:
            return "increasing"
        return "decreasing"

    def flag_abnormal_values(self, lab_results: list[dict[str, Any]]) -> dict[str, Any]:
        """Count abnormal and critical values in a lab result list."""

        abnormal_results = [
            result for result in lab_results if str(result.get("status", "")).upper() in ABNORMAL_STATUSES
        ]
        critical_results = [
            result for result in abnormal_results if str(result.get("status", "")).upper() == "CRITICAL"
        ]

        return {
            "total_results": len(lab_results),
            "abnormal_count": len(abnormal_results),
            "critical_count": len(critical_results),
            "abnormal_results": abnormal_results,
        }

    def calculate_multi_year_pattern(self, lab_results: list[dict[str, Any]]) -> dict[str, Any]:
        """Identify longitudinal pattern and repeated abnormal behavior."""

        sorted_results = sorted(lab_results, key=lambda result: self._parse_date(result.get("collected_at")))
        abnormal_summary = self.flag_abnormal_values(sorted_results)
        values = [float(result["value"]) for result in sorted_results if result.get("value") is not None]

        if len(values) < 2:
            return {
                "pattern_type": "insufficient_data",
                "repeated_abnormal_values": abnormal_summary["abnormal_count"] >= 2,
                "abnormal_count": abnormal_summary["abnormal_count"],
                "critical_count": abnormal_summary["critical_count"],
            }

        deltas = [current - previous for previous, current in zip(values, values[1:])]
        positive = all(delta > 0 for delta in deltas)
        negative = all(delta < 0 for delta in deltas)
        mostly_flat = all(abs(delta) <= max(abs(values[0]) * 0.05, 0.25) for delta in deltas)

        if positive:
            pattern_type = "consistent increase"
        elif negative:
            pattern_type = "consistent decrease"
        elif mostly_flat:
            pattern_type = "stable pattern"
        else:
            pattern_type = "fluctuating pattern"

        return {
            "pattern_type": pattern_type,
            "repeated_abnormal_values": abnormal_summary["abnormal_count"] >= 2,
            "abnormal_count": abnormal_summary["abnormal_count"],
            "critical_count": abnormal_summary["critical_count"],
        }

    def get_abnormal_results_from_scoped_context(
        self,
        recent_lab_results: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Return scoped abnormal results enriched with trend direction per test."""

        abnormal_results: list[dict[str, Any]] = []
        unique_tests = sorted({result["test_name"] for result in recent_lab_results})
        trend_by_test = {
            test_name: self.calculate_lab_trend_from_results(
                patient_id=recent_lab_results[0]["patient_id"] if recent_lab_results else "",
                test_name=test_name,
                lab_results=recent_lab_results,
            ).get("direction", "insufficient_data")
            for test_name in unique_tests
        }

        for result in recent_lab_results:
            status = str(result.get("status", "")).upper()
            if status not in ABNORMAL_STATUSES:
                continue
            abnormal_results.append(
                {
                    "test_name": result.get("test_name"),
                    "date": result.get("collected_at"),
                    "value": result.get("value"),
                    "unit": result.get("unit"),
                    "normal_range": result.get("normal_range"),
                    "status": status,
                    "trend_direction": trend_by_test.get(result.get("test_name"), "insufficient_data"),
                }
            )

        return abnormal_results

    def calculate_lab_trend(
        self,
        patient_id: str,
        test_name: str,
        threshold_percent: float = 5.0,
    ) -> dict[str, Any]:
        """Calculate a deterministic trend summary for one patient's lab test history."""

        safe_result = self._empty_trend_result(patient_id=patient_id, test_name=test_name)
        if not patient_id or not patient_id.strip():
            safe_result["trend_summary"] = "No lab trend could be calculated because patient_id was not provided."
            return safe_result
        if not test_name or not test_name.strip():
            safe_result["trend_summary"] = "No lab trend could be calculated because test_name was not provided."
            return safe_result

        lab_results = self.get_lab_results_by_test(patient_id=patient_id, test_name=test_name)
        return self._calculate_lab_trend_from_records(
            patient_id=patient_id,
            test_name=test_name,
            lab_results=lab_results,
            threshold_percent=threshold_percent,
        )

    def calculate_lab_trend_from_results(
        self,
        patient_id: str,
        test_name: str,
        lab_results: list[dict[str, Any]],
        threshold_percent: float = 5.0,
    ) -> dict[str, Any]:
        """Calculate a trend from a provided privacy-scoped result set."""

        filtered_results = [
            result
            for result in lab_results
            if result.get("patient_id") == patient_id and result.get("test_name") == test_name
        ]
        return self._calculate_lab_trend_from_records(
            patient_id=patient_id,
            test_name=test_name,
            lab_results=filtered_results,
            threshold_percent=threshold_percent,
        )

    def _calculate_lab_trend_from_records(
        self,
        patient_id: str,
        test_name: str,
        lab_results: list[dict[str, Any]],
        threshold_percent: float,
    ) -> dict[str, Any]:
        safe_result = self._empty_trend_result(patient_id=patient_id, test_name=test_name)
        if not lab_results:
            safe_result["trend_summary"] = (
                f"No lab results were found for patient '{patient_id.strip()}' and test '{test_name.strip()}'."
            )
            return safe_result

        sorted_results = sorted(
            lab_results,
            key=lambda result: self._parse_date(result.get("collected_at")),
        )
        abnormal_summary = self.flag_abnormal_values(sorted_results)
        pattern_summary = self.calculate_multi_year_pattern(sorted_results)

        if len(sorted_results) < 2:
            single = sorted_results[0]
            safe_result.update(
                {
                    "first_value": single.get("value"),
                    "first_date": single.get("collected_at"),
                    "latest_value": single.get("value"),
                    "latest_date": single.get("collected_at"),
                    "unit": single.get("unit"),
                    "latest_status": single.get("status"),
                    "abnormal_count": abnormal_summary["abnormal_count"],
                    "total_results": abnormal_summary["total_results"],
                    "trend_summary": (
                        f"Only one {test_name.strip()} result is available for patient "
                        f"'{patient_id.strip()}', so trend analysis is insufficient."
                    ),
                    "pattern_summary": pattern_summary["pattern_type"],
                }
            )
            return safe_result

        first_result = sorted_results[0]
        latest_result = sorted_results[-1]
        first_value = float(first_result["value"])
        latest_value = float(latest_result["value"])
        absolute_change = round(latest_value - first_value, 2)
        percent_change = self._calculate_percent_change(first_value, latest_value)
        direction = self.classify_trend_direction(
            first_value=first_value,
            latest_value=latest_value,
            threshold_percent=threshold_percent,
        )

        return {
            "patient_id": patient_id.strip(),
            "test_name": test_name.strip(),
            "first_value": round(first_value, 2),
            "first_date": first_result.get("collected_at"),
            "latest_value": round(latest_value, 2),
            "latest_date": latest_result.get("collected_at"),
            "unit": latest_result.get("unit"),
            "latest_status": latest_result.get("status"),
            "absolute_change": absolute_change,
            "percent_change": percent_change,
            "direction": direction,
            "abnormal_count": abnormal_summary["abnormal_count"],
            "critical_count": abnormal_summary["critical_count"],
            "total_results": abnormal_summary["total_results"],
            "pattern_summary": pattern_summary["pattern_type"],
            "trend_summary": self._build_trend_summary(
                patient_id=patient_id.strip(),
                test_name=test_name.strip(),
                first_value=first_value,
                latest_value=latest_value,
                unit=latest_result.get("unit"),
                direction=direction,
                abnormal_count=abnormal_summary["abnormal_count"],
                total_results=abnormal_summary["total_results"],
                latest_status=str(latest_result.get("status", "")),
            ),
        }

    @staticmethod
    def _calculate_percent_change(first_value: float, latest_value: float) -> float:
        if first_value == 0:
            return 0.0 if latest_value == 0 else 100.0
        return round(((latest_value - first_value) / abs(first_value)) * 100, 2)

    @staticmethod
    def _parse_date(value: Any) -> datetime:
        if not value:
            return datetime.min
        return datetime.fromisoformat(str(value))

    @staticmethod
    def _empty_trend_result(patient_id: str, test_name: str) -> dict[str, Any]:
        return {
            "patient_id": (patient_id or "").strip(),
            "test_name": (test_name or "").strip(),
            "first_value": None,
            "first_date": None,
            "latest_value": None,
            "latest_date": None,
            "unit": None,
            "latest_status": None,
            "absolute_change": 0.0,
            "percent_change": 0.0,
            "direction": "insufficient_data",
            "abnormal_count": 0,
            "critical_count": 0,
            "total_results": 0,
            "pattern_summary": "insufficient_data",
            "trend_summary": "No data available.",
        }

    @staticmethod
    def _build_trend_summary(
        patient_id: str,
        test_name: str,
        first_value: float,
        latest_value: float,
        unit: str | None,
        direction: str,
        abnormal_count: int,
        total_results: int,
        latest_status: str,
    ) -> str:
        unit_suffix = f" {unit}" if unit else ""
        return (
            f"{test_name} for patient '{patient_id}' is {direction}, changing from "
            f"{round(first_value, 2)}{unit_suffix} to {round(latest_value, 2)}{unit_suffix} "
            f"across {total_results} result(s). Latest status is {latest_status or 'UNKNOWN'} "
            f"with {abnormal_count} abnormal result(s) in the series."
        )
