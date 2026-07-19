# Ops — baseline

> Baseline principles. A project overrides these with a nearer file (project root, then a path-scoped
> subtree). `/start` specializes the `— enforced by:` mechanisms below to the project's actual pipeline.

- Runnable from a clean clone with one documented command — no undocumented local state.
  — enforced by: cold-build check (CI)
- Config comes from the environment, not hardcoded; the required variables are documented.
- Fail loud and early — surface errors, never swallow them into a silent bad state.
- Keep changes reversible — small commits and a rollback path for anything deployed.
- Outward actions (push, deploy, publish) are gated, never silent. — enforced by: permission gate
- Health and log signals exist before you need them, not after the incident.
