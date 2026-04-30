# ADR-001: LLM Provider Strategy

## Status

Accepted for initial foundation planning.

## Context

The project needs a provider strategy that supports local proof-of-concept development now while keeping a clear path to future managed-cloud deployment. Current scope does not yet include live model calls.

## Decision

The backend will use an adapter-oriented provider strategy with configuration support for:

- `openai`
- `vertex`

Provider selection is environment-driven through `LLM_PROVIDER`, while concrete integrations remain isolated behind future client adapters under `llm/`. This provider abstraction lets the application keep the same request flow while swapping or extending model vendors with minimal route-level change.

## Rationale

- Keeps application logic separate from model vendor details
- Supports safer rollout by allowing provider selection without large rewrites
- Aligns with later migration needs toward managed cloud infrastructure
- Avoids hard-coding a single vendor into orchestration logic
- Makes portfolio architecture more reusable across organizations with different provider constraints

## Alternatives Considered

### OpenAI only

Rejected because it would reduce portability and make later cloud migration harder.

### Vertex only

Rejected because it would narrow local and portfolio usability too early.

### Direct SDK calls inside routes

Rejected because it would tightly couple transport, business logic, and provider behavior.

## Consequences

- A base adapter contract will be needed before live model integration
- Provider-specific retries, observability, and guardrails can be added behind the adapter boundary
- Tests can validate provider selection independently of model execution
