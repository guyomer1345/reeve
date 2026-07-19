# Security — baseline

> Baseline principles. A project overrides these with a nearer file (project root, then a path-scoped
> subtree). `/start` specializes the `— enforced by:` mechanisms below to the project's actual tooling.

- No secret in the repo, ever — read it from the environment or a secret store; a placeholder stands in the
  code. — enforced by: secret-scan gate
- Validate and encode at trust boundaries (input in, output out); never build a query or shell command by
  string concatenation. — enforced by: linter / static analysis where available
- Least privilege for every token, key, and role — grant the narrowest scope that works.
- Dependencies are attack surface — pin them, audit them, and update deliberately, not blindly.
  — enforced by: dependency audit (CI)
- Never log secrets or personal data.
- A destructive or irreversible operation needs a verified backup or an explicit human gate before it runs.
