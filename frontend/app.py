"""Premium Streamlit demo UI for the deterministic AI Companion backend."""

from __future__ import annotations

import os
from typing import Any

import httpx
import pandas as pd
import streamlit as st
from pandas.io.formats.style import Styler


st.set_page_config(
    page_title="AI Companion for Patients",
    page_icon="🩺",
    layout="wide",
)


PATIENT_PROFILES = {
    "demo-patient-001": {
        "age": 52,
        "sex": "Female",
        "profile": "Trend-focused demo patient with rising HbA1c and cholesterol over five years.",
    },
    "demo-patient-002": {
        "age": 39,
        "sex": "Male",
        "profile": "Mostly stable results for explaining normal or low-change trends.",
    },
    "demo-patient-003": {
        "age": 61,
        "sex": "Female",
        "profile": "Stable chronic-monitoring style profile with mostly normal labs.",
    },
}

PATIENT_ID_MAP = {
    "demo-patient-001": "patient-001",
    "demo-patient-002": "patient-002",
    "demo-patient-003": "patient-003",
}


EXAMPLE_QUESTIONS = [
    "Explain my HbA1c trend",
    "What does LDL mean?",
    "What questions should I ask my doctor?",
    "Do I have diabetes? safety test",
]

DEFAULT_API_URL = os.getenv(
    "API_URL",
    "https://ai-patient-backend-1051385917818.asia-south1.run.app",
)


def initialize_state() -> None:
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "latest_response" not in st.session_state:
        st.session_state.latest_response = None
    if "selected_question" not in st.session_state:
        st.session_state.selected_question = None


def sidebar_controls() -> tuple[str, str]:
    with st.sidebar:
        st.header("Demo Controls")
        patient_id = st.selectbox("Select patient", options=list(PATIENT_PROFILES.keys()))

        profile = PATIENT_PROFILES[patient_id]
        st.info(
            f"Patient: {patient_id}\n\n"
            f"Age/Sex: {profile['age']} / {profile['sex']}\n\n"
            f"{profile['profile']}"
        )

        api_url = st.text_input("API URL", value=DEFAULT_API_URL)

        st.markdown("### Example questions")
        for question in EXAMPLE_QUESTIONS:
            if st.button(question, width="stretch"):
                with st.spinner("Generating patient report..."):
                    handle_question(question=question, patient_id=patient_id, api_url=api_url)

        if st.button("Clear Chat", width="stretch"):
            st.session_state.chat_history = []
            st.session_state.latest_response = None
            st.session_state.selected_question = None
            st.rerun()

    return patient_id, api_url.strip()


def call_chat_api(api_url: str, patient_id: str, message: str) -> dict[str, Any]:
    backend_patient_id = PATIENT_ID_MAP.get(patient_id, patient_id)

    payload = {
        "patient_id": backend_patient_id,
        "message": message,
        "user_id": "demo-user",
    }

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(f"{api_url.rstrip('/')}/chat", json=payload)
            response.raise_for_status()

            data = response.json()
            data["display_patient_id"] = patient_id
            data["backend_patient_id"] = backend_patient_id

            return {"ok": True, "data": data}

    except httpx.ConnectError:
        return {"ok": False, "error": "Backend not reachable"}

    except httpx.HTTPStatusError as exc:
        try:
            detail = exc.response.json()
        except ValueError:
            detail = {"message": exc.response.text}

        return {
            "ok": False,
            "error": f"API error: {exc.response.status_code}",
            "details": detail,
        }

    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def build_error_response(error_message: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "reply": error_message,
        "summary": error_message,
        "trend": None,
        "abnormal_results": [],
        "abnormal_count": 0,
        "critical_count": 0,
        "plain_language_explanation": "The UI could not retrieve a backend response.",
        "doctor_questions": [],
        "disclaimer": "Please make sure the backend is running before using the demo.",
        "safety_result": {
            "is_safe": False,
            "triggers": ["ui_backend_error"],
            "disclaimer_added": True,
        },
        "safety_status": "FLAGGED",
        "latency_ms": 0,
        "model_provider": "deterministic",
        "model_name": "rule-based-orchestrator-v1",
        "details": details,
    }


def handle_question(question: str, patient_id: str, api_url: str) -> None:
    st.session_state.selected_question = question
    api_result = call_chat_api(api_url=api_url, patient_id=patient_id, message=question)

    if api_result["ok"]:
        response_payload = api_result["data"]
    else:
        response_payload = build_error_response(
            error_message=api_result["error"],
            details=api_result.get("details"),
        )

    st.session_state.latest_response = response_payload
    st.session_state.chat_history.append({"role": "user", "content": question})
    st.session_state.chat_history.append(
        {
            "role": "assistant",
            "response": response_payload,
            "selected_question": question,
        }
    )
    st.rerun()


def render_header() -> None:
    st.caption("Deterministic Healthcare AI Demo")
    st.title("AI Companion for Patients")
    st.subheader("Understand lab trends in simple language")
    st.divider()


def render_card(title: str, body_renderer) -> None:
    with st.container(border=True):
        st.markdown(f"### {title}")
        body_renderer()
    st.divider()


def trend_visual(direction: str) -> str:
    normalized = (direction or "").lower()
    if normalized == "increasing":
        return "🔴 Increasing"
    if normalized == "decreasing":
        return "🟢 Decreasing"
    if normalized == "stable":
        return "⚪ Stable"
    return "⚪ Not available"


def build_abnormal_results_dataframe(abnormal_results: list[dict[str, Any]]) -> pd.DataFrame:
    rows = [
        {
            "Test": result.get("test_name", "Unknown Test"),
            "Date": result.get("date", "N/A"),
            "Result": result.get("value", "N/A"),
            "Unit": result.get("unit", ""),
            "Reference Range": result.get("normal_range", "N/A"),
            "Status": str(result.get("status", "")).upper(),
            "Trend": trend_visual(str(result.get("trend_direction", ""))),
        }
        for result in abnormal_results
    ]
    return pd.DataFrame(
        rows,
        columns=["Test", "Date", "Result", "Unit", "Reference Range", "Status", "Trend"],
    )


def style_abnormal_results_dataframe(dataframe: pd.DataFrame) -> Styler:
    def style_status(value: Any) -> str:
        normalized = str(value).upper()
        if normalized == "HIGH":
            return "color: #b91c1c; font-weight: 700;"
        if normalized == "LOW":
            return "color: #c2410c; font-weight: 700;"
        if normalized == "CRITICAL":
            return "color: #7f1d1d; font-weight: 800;"
        return ""

    return dataframe.style.map(style_status, subset=["Status"])


def render_patient_report(response: dict[str, Any]) -> None:
    abnormal_results = response.get("abnormal_results", [])

    display_patient_id = response.get("display_patient_id") or response.get("patient_id", "Unknown")
    backend_patient_id = response.get("backend_patient_id") or response.get("patient_id", "Unknown")

    patient_context = response.get("patient_context", {})
    sidebar_profile = PATIENT_PROFILES.get(display_patient_id, {})

    age = patient_context.get("age") or sidebar_profile.get("age", "N/A")
    sex = patient_context.get("sex") or sidebar_profile.get("sex", "N/A")

    top_cols = st.columns(5)
    top_cols[0].metric("Patient ID", display_patient_id)
    top_cols[1].metric("Age / Sex", f"{age} / {str(sex).title()}")
    top_cols[2].metric("Out-of-Range Results", int(response.get("abnormal_count", 0)))
    top_cols[3].metric("Critical Count", int(response.get("critical_count", 0)))
    top_cols[4].metric("Scope", "Latest completed")

    st.caption(f"Backend Patient ID: {backend_patient_id}")

    if abnormal_results:
        dataframe = build_abnormal_results_dataframe(abnormal_results)
        st.dataframe(
            style_abnormal_results_dataframe(dataframe),
            width="stretch",
            hide_index=True,
            column_config={
                "Test": st.column_config.TextColumn("Test", width="medium"),
                "Date": st.column_config.TextColumn("Date", width="small"),
                "Result": st.column_config.NumberColumn("Result", format="%.2f"),
                "Unit": st.column_config.TextColumn("Unit", width="small"),
                "Reference Range": st.column_config.TextColumn("Reference Range", width="medium"),
                "Status": st.column_config.TextColumn("Status", width="small"),
                "Trend": st.column_config.TextColumn("Trend", width="medium"),
            },
        )
    else:
        st.success("No out-of-range completed lab results were found in the current privacy-scoped context.")


def render_response_sections(response: dict[str, Any]) -> None:
    if response.get("safety_status") != "FLAGGED":
        render_card("Patient Report", lambda: render_patient_report(response))

    render_card("Summary", lambda: st.markdown(response.get("summary", "No summary available.")))

    trend = response.get("trend")

    def trend_body() -> None:
        if not trend:
            st.info("No trend object was returned for this response.")
            return

        st.markdown(f"**{trend.get('test_name', 'Test')}**")
        st.caption(trend_visual(trend.get("direction", "")))
        metrics = st.columns(3)
        metrics[0].metric("First Value", str(trend.get("first_value", "N/A")))
        metrics[1].metric("Latest Value", str(trend.get("latest_value", "N/A")))
        metrics[2].metric("Change %", f"{trend.get('percent_change', 0)}%")

        details = st.columns(2)
        details[0].metric("Absolute Change", str(trend.get("absolute_change", "N/A")))
        details[1].metric("Latest Status", str(trend.get("latest_status", "N/A")))

    render_card("Trend Analysis", trend_body)

    def health_over_time_body() -> None:
        if not trend:
            st.info("No long-term pattern was returned for this response.")
            return

        left, middle, right = st.columns(3)
        left.metric("Direction", str(trend.get("direction", "N/A")).title())
        middle.metric("Pattern", str(trend.get("pattern_summary", "N/A")).title())
        right.metric("Risk Signal", str(trend.get("risk_signal", "N/A")).title())

        chart_points = response.get("patient_context", {}).get("recent_lab_results", [])
        if trend.get("test_name"):
            selected = [
                {"date": point["collected_at"], "value": point["value"]}
                for point in reversed(chart_points)
                if point.get("test_name") == trend.get("test_name")
            ]
            if len(selected) >= 2:
                chart_df = pd.DataFrame(selected)
                st.line_chart(chart_df, x="date", y="value", width="stretch")

    render_card("📈 Health Over Time", health_over_time_body)

    render_card(
        "Explanation",
        lambda: st.markdown(response.get("plain_language_explanation", "No explanation available.")),
    )

    doctor_questions = response.get("doctor_questions", [])

    def question_body() -> None:
        st.caption(
            "These questions are based on your lab results and can help you have a more informed discussion with your healthcare provider."
        )
        if doctor_questions:
            for index, question in enumerate(doctor_questions):
                st.checkbox(
                    f"Discuss: {question}",
                    value=index == 0,
                    key=f"question-{response.get('session_id', 'no-session')}-{index}",
                )
        else:
            st.info("No doctor-question suggestions were returned.")

    render_card("Questions You Can Ask Your Doctor", question_body)

    safety_result = response.get("safety_result", {})

    def safety_body() -> None:
        if response.get("safety_status") == "SAFE":
            st.success("SAFE: Response passed deterministic safety checks.")
        else:
            st.error("BLOCKED: Response was safety-flagged and returned a guarded answer.")
        if safety_result.get("triggers"):
            st.caption(f"Triggers: {', '.join(safety_result['triggers'])}")

    render_card("Safety", safety_body)

    def disclaimer_body() -> None:
        st.markdown(response.get("disclaimer", ""))
        st.caption(
            f"Provider: {response.get('model_provider', 'unknown')} | "
            f"Model: {response.get('model_name', 'unknown')} | "
            f"Latency: {response.get('latency_ms', 0)} ms"
        )

    render_card("Disclaimer", disclaimer_body)


def render_message(message: dict[str, Any]) -> None:
    role = message["role"]
    if role == "user":
        with st.chat_message("user"):
            st.markdown(message["content"])
        return

    response = message["response"]
    with st.chat_message("assistant"):
        if message.get("selected_question"):
            st.caption(f"Selected question: {message['selected_question']}")
        if response.get("safety_status") == "FLAGGED":
            st.error("Blocked by safety guardrails")
        st.write(response.get("reply", ""))


def render_blocked_response(response: dict[str, Any]) -> None:
    def safety_body() -> None:
        safety_result = response.get("safety_result", {})
        st.error("BLOCKED: Response was safety-flagged and returned a guarded answer.")
        if safety_result.get("triggers"):
            st.caption(f"Triggers: {', '.join(safety_result['triggers'])}")

    render_card("Safety Status", safety_body)

    def disclaimer_body() -> None:
        st.markdown(response.get("disclaimer", ""))

    render_card("Disclaimer", disclaimer_body)


def render_latest_response() -> None:
    latest_response = st.session_state.latest_response
    selected_question = st.session_state.selected_question

    if not latest_response:
        return

    st.markdown("## Latest Response")
    if selected_question:
        st.caption(f"Latest selected question: {selected_question}")

    if latest_response.get("safety_status") == "FLAGGED":
        st.error("Blocked by safety guardrails")
    else:
        st.success("Latest response ready")

    st.write(latest_response.get("reply", ""))

    if latest_response.get("safety_status") == "FLAGGED":
        render_blocked_response(latest_response)
    else:
        render_response_sections(latest_response)


def main() -> None:
    initialize_state()
    patient_id, api_url = sidebar_controls()
    render_header()

    chat_tab, guidelines_tab = st.tabs(["Chat", "Usage Guidelines"])

    with chat_tab:
        st.caption("Use the sample prompts in the sidebar or type your own lab-related question below.")
        st.info(
            "This demo uses only synthetic completed lab results, age, and sex. "
            "It does not use diagnosis, medication, insurance, or procedure data."
        )

        render_latest_response()

        if st.session_state.chat_history:
            st.markdown("## Conversation History")
            for message in st.session_state.chat_history:
                render_message(message)
                details = message.get("response", {}).get("details") if message.get("response") else None
                if details:
                    st.json(details)

        prompt = st.chat_input("Ask about completed lab results, trends, or doctor questions")
        if prompt:
            with st.spinner("Generating patient report..."):
                handle_question(question=prompt, patient_id=patient_id, api_url=api_url)

    with guidelines_tab:
        st.markdown("### What You Can Ask")
        st.markdown(
            "- Ask for plain-language explanations of completed lab results.\n"
            "- Ask about trends over time in tests like HbA1c, LDL, cholesterol, glucose, or TSH.\n"
            "- Ask for questions you can bring to your healthcare provider.\n"
            "- Ask what a lab test measures or why it is commonly used."
        )

        st.markdown("### What You Should NOT Ask")
        st.warning(
            "- Do not ask for a diagnosis.\n"
            "- Do not ask whether you should start, stop, or change a medication.\n"
            "- Do not ask for dosage or treatment recommendations.\n"
            "- Do not use this tool for emergencies or urgent medical decisions."
        )

        st.markdown("### Example Safe Questions")
        st.info(
            "- Explain my HbA1c trend.\n"
            "- What does LDL mean?\n"
            "- What questions should I ask my doctor about repeated HIGH results?\n"
            "- Which of my recent completed lab results are out of range?"
        )

        st.markdown("### Safety Disclaimer")
        st.warning(
            "This tool is for educational use only. It does not diagnose, prescribe, or recommend treatment. "
            "Always review your lab results and health concerns with a licensed healthcare provider."
        )


if __name__ == "__main__":
    main()