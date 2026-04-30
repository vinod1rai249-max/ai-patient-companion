# Requirements Traceability

This matrix maps current project requirements to implementation and validation evidence.

| Requirement ID | Requirement | Code file | Test file | Validation status |
| --- | --- | --- | --- | --- |
| R-001 | Load app configuration from environment with safe defaults | `backend/config.py` | `tests/test_contracts.py` | Implemented and tested |
| R-002 | Create SQLite database path and foundational tables | `backend/database.py` | `tests/test_chat_api.py` | Implemented and indirectly tested |
| R-003 | Provide a health endpoint | `backend/main.py` | `tests/test_chat_api.py` | Implemented and tested |
| R-004 | Return a safe placeholder chat response with disclaimer and response contract fields | `backend/main.py`, `backend/models.py` | `tests/test_chat_api.py`, `tests/test_contracts.py` | Implemented and tested |
| R-005 | Accept feedback with validated rating values | `backend/main.py`, `backend/models.py`, `backend/database.py` | `tests/test_chat_api.py`, `tests/test_contracts.py` | Implemented and tested |
| R-006 | Keep safety tests present in the repository | `tests/test_safety.py` | `tests/test_safety.py` | Implemented and tested |
| R-007 | Support provider abstraction and optional OpenRouter wording enhancement without replacing deterministic source-of-truth fields | `backend/config.py`, `llm/base.py`, `llm/openai_client.py`, `agents/orchestrator.py` | `tests/test_contracts.py`, `tests/test_agents.py` | Implemented and tested |
| R-008 | Enforce governance checks for project structure and secret hygiene | `scripts/validate_project.py`, `scripts/check_no_secrets.py` | `tests/test_contracts.py` | Implemented and manually validated |
| R-009 | Generate synthetic patients with five years of lab history for demo use only | `data/generate_data.py` | `tests/test_data_pipeline.py` | Implemented and tested |
| R-010 | Load synthetic patient and lab data into SQLite without duplicating demo history | `data/load_data.py`, `backend/database.py` | `tests/test_data_pipeline.py` | Implemented and tested |
| R-011 | Provide deterministic patient lab retrieval and trend analysis tools with no LLM dependency | `tools/lab_tools.py`, `backend/database.py` | `tests/test_trend_analysis.py` | Implemented and tested |
| R-012 | Count abnormal lab values using status-based rules | `tools/lab_tools.py` | `tests/test_trend_analysis.py` | Implemented and tested |
| R-013 | Detect unsafe diagnosis, medication, emergency, and prompt-injection requests deterministically | `tools/safety_tools.py` | `tests/test_safety.py` | Implemented and tested |
| R-014 | Validate assistant responses so they do not diagnose, prescribe, or omit the provider disclaimer | `tools/safety_tools.py` | `tests/test_safety.py` | Implemented and tested |
| R-015 | Provide a deterministic patient context agent that returns structured lab context | `agents/patient_context_agent.py`, `tools/lab_tools.py` | `tests/test_agents.py` | Implemented and tested |
| R-016 | Provide a deterministic trend analysis agent that summarizes patient test trends | `agents/trend_analysis_agent.py`, `tools/lab_tools.py` | `tests/test_agents.py` | Implemented and tested |
| R-017 | Provide a deterministic explanation agent with static test definitions | `agents/explanation_agent.py` | `tests/test_agents.py` | Implemented and tested |
| R-018 | Provide a deterministic doctor question agent driven by trend rules | `agents/doctor_question_agent.py` | `tests/test_agents.py` | Implemented and tested |
| R-019 | Provide a deterministic safety guardrail agent for user and final-response validation | `agents/safety_guardrail_agent.py`, `tools/safety_tools.py` | `tests/test_agents.py` | Implemented and tested |
| R-020 | Provide a deterministic orchestrator that coordinates all agents for a `ChatRequest` | `agents/orchestrator.py`, `backend/models.py` | `tests/test_agents.py` | Implemented and tested |
| R-021 | Connect `/chat` to the deterministic orchestrator and return a structured deterministic response contract | `backend/main.py`, `agents/orchestrator.py`, `backend/models.py` | `tests/test_chat_api.py`, `tests/test_contracts.py` | Implemented and tested |
| R-022 | Persist each chat interaction, including blocked safety requests, into SQLite | `backend/database.py`, `backend/main.py` | `tests/test_chat_api.py` | Implemented and tested |
| R-023 | Limit patient context to age, sex, and up to 20 recent completed lab results less than 5 years old | `backend/database.py`, `agents/patient_context_agent.py`, `agents/orchestrator.py` | `tests/test_data_pipeline.py`, `tests/test_agents.py` | Implemented and tested |
| R-024 | Show out-of-range completed lab results first and prioritize abnormal findings in the patient report experience | `tools/lab_tools.py`, `agents/orchestrator.py`, `backend/models.py`, `frontend/app.py` | `tests/test_trend_analysis.py`, `tests/test_agents.py`, `tests/test_chat_api.py` | Implemented and tested |
