# Definition of Done

## Checklist

- [ ] Scope is implemented or explicitly marked deferred
- [ ] Code changes are small, focused, and avoid unrelated rewrites
- [ ] Inputs and response contracts are validated where applicable
- [ ] Relevant tests cover success behavior
- [ ] Relevant tests cover validation failure behavior where applicable
- [ ] `python -m pytest tests -q` passes in a prepared environment
- [ ] `python scripts/validate_project.py` passes
- [ ] `python scripts/check_no_secrets.py` passes
- [ ] User-facing healthcare messaging includes a provider disclaimer
- [ ] The change does not introduce diagnosis, prescribing, or treatment recommendation behavior
- [ ] Documentation reflects the current implementation state
- [ ] Rollback risk is low because the change is isolated
