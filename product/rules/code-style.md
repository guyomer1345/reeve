# Code style — baseline

> Baseline principles. A project overrides these with a nearer file — a `rules/` at the project root beats
> this baseline, and a `rules/` inside a subtree beats the project root for files under it. `/start`
> specializes the `— enforced by:` mechanisms below to the project's actual tools.

- Formatting is machine-owned, not argued — a formatter runs on every change; never hand-format or bikeshed
  whitespace in review. — enforced by: formatter + `.editorconfig`
- One style per language; the linter is the source of truth, not review comments. — enforced by: linter
- Type the boundaries — public functions and module edges carry explicit types; internals may infer.
  — enforced by: typechecker
- Names say *what*, not *how*; delete dead and commented-out code — the history remembers it.
- Small, single-purpose units — a function that needs a paragraph to explain its branches is two functions.
- Match the surrounding code's idiom over personal preference; consistency beats local cleverness.
