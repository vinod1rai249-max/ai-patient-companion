"""Deterministic lab explanation agent."""

from __future__ import annotations

from typing import Any


TEST_DEFINITIONS = {
    "HbA1c": "HbA1c estimates average blood sugar levels over the past two to three months.",
    "Total Cholesterol": "Total Cholesterol measures the total amount of cholesterol in your blood.",
    "LDL": "LDL is often called bad cholesterol because higher levels can raise heart risk.",
    "HDL": "HDL is often called good cholesterol because it helps carry cholesterol away from the bloodstream.",
    "Fasting Glucose": "Fasting Glucose measures blood sugar after not eating for a period of time.",
    "TSH": "TSH is a thyroid-related test used to understand how your thyroid is being signaled.",
    "Creatinine": "Creatinine is commonly used as one marker related to kidney function.",
    "Hemoglobin": "Hemoglobin measures the oxygen-carrying protein in red blood cells.",
    "WBC": "WBC measures white blood cell count, which can help describe immune system activity.",
}


class ExplanationAgent:
    """Return simple static explanations for lab test names."""

    def run(self, test_names: list[str]) -> dict[str, Any]:
        explanations = {
            test_name: TEST_DEFINITIONS.get(
                test_name,
                "A simple explanation is not available yet for this test name.",
            )
            for test_name in test_names
        }
        return {"explanations": explanations}
