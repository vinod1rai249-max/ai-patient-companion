# AI Companion for Patients

A portfolio-ready GenAI healthcare assistant prototype that helps patients understand completed lab results, spot trends over time, learn medical terms in plain language, and prepare thoughtful questions for their healthcare provider.

## Project Scope

This project is a generic healthcare proof of concept inspired by public AI companion requirements.

It is intentionally designed to:

- Explain completed lab results in simple language
- Explain the purpose of each lab test
- Identify trends from historical lab data
- Help patients prepare questions for their healthcare provider
- Use only provided patient lab data, age, and sex
- Avoid medications, diagnoses, medical procedures, and external uploaded documents
- Avoid diagnosis, prescribing, and treatment recommendations
- Always include a healthcare provider disclaimer
- Capture feedback, safety triggers, latency, and response quality signals

## Tech Stack

- Python 3.11+
- FastAPI backend
- Streamlit frontend
- SQLite for local proof of concept
- Pydantic for validation
- Adapter-based LLM layer for OpenAI or Vertex AI Gemini
- Agent-oriented orchestration
- Local logging and evaluation harness

## Architecture Overview

The system will be built around a central orchestrator coordinating:

1. `PatientContextAgent`
2. `LabTrendAnalysisAgent`
3. `MedicalTermExplanationAgent`
4. `DoctorQuestionAgent`
5. `SafetyGuardrailAgent`
6. `ResponseQualityEvaluatorAgent`

## Planned Tooling

1. `get_patient_lab_results(patient_id)`
2. `calculate_lab_trends(patient_id, test_name)`
3. `classify_lab_status(value, normal_range)`
4. `generate_doctor_questions(context)`
5. `validate_safety(response)`
6. `log_interaction(event)`

## Current Status

The current build delivers a deterministic patient-report-first experience on top of the FastAPI backend:

- Environment-based configuration
- Pydantic request and response models
- SQLite database manager and table creation
- Structured logging
- FastAPI health, chat, and feedback endpoints
- Synthetic patient generation with 5 years of lab history
- SQLite loader for demo patient and lab data
- Deterministic lab trend analysis tools with no LLM dependency
- Deterministic user-message and AI-response safety validation tools
- Deterministic patient context, trend, explanation, question, safety, and orchestration agents
- Deterministic `/chat` API responses backed by the orchestrator
- Optional OpenRouter language enhancement for `summary` and `plain_language_explanation` only
- SQLite interaction persistence for safe and blocked conversations
- Premium Streamlit UI for demoing structured healthcare responses
- Patient Report section that shows out-of-range completed lab results before secondary trend insights
- Automated tests for backend contracts, data generation, persistence, trend analysis, safety checks, agent behavior, and `/chat` behavior

The deterministic pipeline remains the source of truth. When enabled, OpenRouter is used only to improve wording, and guardrails can fall back to deterministic text automatically.

## Run Plan

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Start the API:

```bash
python -m uvicorn backend.main:app --reload
```

Start Streamlit:

```bash
streamlit run frontend/app.py
```

Generate synthetic data:

```bash
python data/generate_data.py
```

Load synthetic data into SQLite:

```bash
python data/load_data.py
```

Run tests:

```bash
python -m pytest tests -q
```

## OpenRouter Setup

Copy values from [.env.example](C:\Users\vinod%20rai\Documents\Codex\2026-04-30\you-are-a-senior-genai-architect\ai_patient_companion\.env.example) into your local `.env` file and set:

- `OPENAI_API_KEY` to your OpenRouter key
- `OPENAI_BASE_URL` to the OpenRouter API base URL
- `OPENAI_MODEL` to the OpenRouter model you want to use
- `LLM_TIMEOUT_SECONDS` to your preferred request timeout

Run in deterministic mode:

```bash
set LLM_PROVIDER=deterministic
python -m uvicorn backend.main:app --reload
```

Run in OpenRouter mode:

```bash
set LLM_PROVIDER=openrouter
python -m uvicorn backend.main:app --reload
```

In OpenRouter mode, the app still keeps deterministic tools as the source of truth. Only `summary` and `plain_language_explanation` are eligible for wording improvements, and failures fall back automatically to deterministic responses.

Call the trend tool directly from Python:

```bash
python -c "from tools.lab_tools import LabTools; result = LabTools().calculate_lab_trend('demo-patient-001', 'HbA1c'); print(result)"
```

Example trend output:

```text
{
  'patient_id': 'demo-patient-001',
  'test_name': 'HbA1c',
  'first_value': 5.6,
  'latest_value': 7.0,
  'direction': 'increasing',
  'abnormal_count': 4,
  'total_results': 5,
  ...
}
```

Call the safety tool directly from Python:

```bash
python -c "from tools.safety_tools import validate_user_message; print(validate_user_message('Do I have diabetes?'))"
```

Example safety output:

```text
{
  'is_safe': False,
  'category': 'diagnosis_request',
  'triggers': ['diagnosis_request'],
  'allow': False,
  'refusal_message': 'I cannot diagnose medical conditions. This information is for education only and is not medical advice. Please review your lab results and any concerns with your healthcare provider.'
}
```

Call the orchestrator directly from Python:

```bash
python -c "from agents.orchestrator import Orchestrator; from backend.models import ChatRequest; result = Orchestrator().run(ChatRequest(patient_id='demo-patient-001', message='Explain my HbA1c trend')); print(result)"
```

Example orchestrator output:

```text
{
  'session_id': '...',
  'reply': 'Trend summary: ... Questions for your doctor: ... This information is for education only and is not medical advice. Please review your lab results and any concerns with your healthcare provider.',
  'safety_status': 'SAFE',
  'patient_context': {...},
  'trend_analysis': {...},
  'doctor_questions': [...]
}
```

Call the `/chat` endpoint with a trend question:

```bash
curl -X POST http://127.0.0.1:8000/chat -H "Content-Type: application/json" -d "{\"patient_id\":\"demo-patient-001\",\"message\":\"Explain my HbA1c trend\"}"
```

Call the `/chat` endpoint with a blocked diagnosis request:

```bash
curl -X POST http://127.0.0.1:8000/chat -H "Content-Type: application/json" -d "{\"patient_id\":\"demo-patient-001\",\"message\":\"Do I have diabetes?\"}"
```

Example `/chat` response shape:

```text
{
  "session_id": "...",
  "patient_id": "demo-patient-001",
  "response_type": "trend_analysis",
  "summary": "Over the past 5 years, your HbA1c has consistently increased and is now in the HIGH range.",
  "abnormal_results": [
    {
      "test_name": "HbA1c",
      "date": "2026-06-15",
      "value": 7.0,
      "unit": "%",
      "normal_range": "4.0-5.6",
      "status": "HIGH",
      "trend_direction": "increasing"
    }
  ],
  "abnormal_count": 7,
  "critical_count": 0,
  "trend": {
    "test_name": "HbA1c",
    "direction": "increasing",
    "pattern_summary": "consistent increase",
    "risk_signal": "high",
    "first_value": 5.6,
    "latest_value": 7.0,
    "absolute_change": 1.4,
    "percent_change": 25.0,
    "latest_status": "HIGH"
  },
  "plain_language_explanation": "HbA1c reflects your average blood sugar over the past two to three months.",
  "doctor_questions": [
    "What could explain the increase in HbA1c over time?",
    "How should I understand the latest HbA1c result being marked HIGH?"
  ],
  "reply": "Your HbA1c trend is increasing. Consider asking: What could explain the increase in HbA1c over time? This information is for education only and is not medical advice. Please review your lab results and any concerns with your healthcare provider.",
  "disclaimer": "...",
  "safety_result": {
    "is_safe": true,
    "triggers": [],
    "disclaimer_added": true
  },
  "latency_ms": 12.3,
  "tools_used": ["PatientContextAgent", "TrendAnalysisAgent", "..."],
  "model_provider": "deterministic",
  "model_name": "rule-based-orchestrator-v1"
}
```

## Demo Flow

1. Start the backend API.
2. Generate and load demo data.
3. Start Streamlit with `streamlit run frontend/app.py`.
4. Select `demo-patient-001` in the sidebar.
5. Click `Explain my HbA1c trend` to show the Patient Report with out-of-range results first.
6. Scroll down to review the supporting trend, explanation, and doctor-question sections.
7. Click `Do I have diabetes? safety test` to show the guardrail behavior.

## Example Questions

- Explain my HbA1c trend
- What does LDL mean?
- What questions should I ask my doctor?
- Do I have diabetes?

## Troubleshooting

- If Streamlit says the backend cannot be reached, confirm FastAPI is running on `http://127.0.0.1:8000`.
- If you changed the backend port, update the API URL in the Streamlit sidebar.
- If `/chat` returns a validation error, check that a patient is selected and the prompt is at least 2 characters long.
- If the demo has no trend data, rerun `python data/generate_data.py` and `python data/load_data.py`.

## Privacy Scope

- Synthetic data only
- Uses at most 20 completed lab results less than 5 years old
- Uses age and sex only for patient context
- No real patient data
- No public model training

Optional local checks:

```bash
curl http://127.0.0.1:8000/health
curl -X POST http://127.0.0.1:8000/chat -H "Content-Type: application/json" -d "{\"patient_id\":\"demo-patient-001\",\"message\":\"Explain my glucose result\"}"
```

## Safety Notice

This project is for educational and portfolio purposes only. It does not provide medical diagnosis, treatment, or prescribing advice. Patients should always consult a licensed healthcare provider for medical decisions.
