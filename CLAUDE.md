# CLAUDE.md

## Project Rules

This repository is for building a safe, production-minded AI Companion for Patients portfolio project in small, validated increments.

## Requirement Traceability Rule

- Every implemented requirement should be traceable to code, tests, and validation status.
- Update `docs/requirements_traceability.md` whenever a meaningful requirement is added, implemented, deferred, or changed.
- Do not present a requirement as complete unless code and validation evidence both exist.

## Definition of Done

A change is done only when:

- Scope is implemented or explicitly deferred
- Relevant tests exist for happy path and validation failure path where applicable
- `scripts/validate_project.py` passes
- `scripts/check_no_secrets.py` passes
- User-facing healthcare responses keep the provider disclaimer requirement intact
- Documentation reflects the current state

## LLM Response Contract

Until live model integration is added, backend response contracts must remain stable and explicit.

Current `/chat` response contract must include:

- `session_id`
- `reply`
- `disclaimer`
- `safety`
- `safety_status`
- `latency_ms`
- `feedback_enabled`

Any future LLM-backed implementation must preserve this contract unless the contract, tests, and docs are updated together.

## Healthcare Safety Rules

- Use only approved patient context for the implemented scope
- Do not diagnose
- Do not prescribe
- Do not recommend treatment
- Always include a healthcare provider disclaimer in patient-facing result explanations
- Log and test safety-sensitive behavior as the project grows

## ADR Rules

- Record architecture decisions under `docs/adr/`
- Use incremental ADR numbering
- Include `Status`, `Context`, `Decision`, `Rationale`, `Alternatives Considered`, and `Consequences`
- Add or update an ADR when introducing a material design decision such as provider strategy, persistence strategy, safety architecture, or orchestration approach
