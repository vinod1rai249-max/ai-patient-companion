"""Deterministic doctor question generation agent."""

from __future__ import annotations

from typing import Any


class DoctorQuestionAgent:
    """Generate rule-based doctor questions from trend outputs."""

    def run(self, trends: list[dict[str, Any]]) -> dict[str, Any]:
        questions: list[str] = []

        for trend in trends:
            test_name = trend.get("test_name", "this test")
            direction = trend.get("direction")
            latest_status = str(trend.get("latest_status", ""))
            abnormal_count = int(trend.get("abnormal_count", 0))
            pattern_summary = str(trend.get("pattern_summary", ""))

            if abnormal_count > 1:
                questions.append(
                    f"Are these repeated {latest_status or 'out-of-range'} {test_name} results concerning?"
                )
            if direction == "increasing":
                questions.append(
                    f"What lifestyle changes could help stabilize my {test_name} trend?"
                )
                questions.append(
                    f"Should I monitor {test_name} more frequently?"
                )
            elif direction == "decreasing":
                questions.append(
                    f"What could explain the decrease in {test_name} over time?"
                )

            if latest_status in {"HIGH", "LOW", "CRITICAL"}:
                questions.append(
                    f"How should I understand the latest {test_name} result being marked {latest_status}?"
                )

            if pattern_summary in {"consistent increase", "consistent decrease"}:
                questions.append(
                    f"What long-term factors might be affecting my {test_name} over time?"
                )

        if not questions:
            questions.append("Are my lab results generally stable over time?")

        return {"doctor_questions": list(dict.fromkeys(questions))}
