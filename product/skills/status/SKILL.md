---
name: status
description: Answer "where is this project" — what's done, how the pieces connect, what's left, and what is blocked on you. Synthesized fresh from the project's own spec, code map, backlog, items and git; never a stored document. Use when a human asks where things stand, when returning to a project after time away, or at a phase boundary.
---

# Status — where is this project

A project's state is real but **scattered**: intent is in the spec, what's left is in the backlog, how it
connects is in the code map, what actually landed is in git and `.workflow/items/`. Answering "where is
this?" meant opening five things and holding them in your head, so nobody did — and the answer drifted.
This capability answers it in one pass.

## The one rule: generated, never stored

**Never write this to a file.** A synthesized status document is stale the moment the next commit lands,
and a stale status document is worse than none because it is *believed*. Run it again instead — it is
cheap. If a human asks for something durable, that is a spec or a decision record, not this.

## Workflow

1. **Gather the mechanical half:**
   ```bash
   python3 .claude/scripts/project_state.py
   ```
   Add `--json` when you want the raw structure to reason over rather than the rendered text. The script
   settles only what a machine can settle exactly — counts, frontmatter, path resolution, centrality
   ranking. It does not judge, and it does not guess: **a section whose source is missing says so** rather
   than inferring from something else.

2. **Read the sources it names, but only where the answer needs it.** The output cites a real path per
   section. Open the spec if the human asked *what are we building*; open the code map's top files if they
   asked *what will this change break*. Do **not** read `graph.json` whole — the script already took the
   bounded top-N per lens, which is the read the memory model allows.

3. **Narrate the part the script deliberately did not.** This is your job, and it is the whole value added:
   - **What the numbers mean.** "4 commitment tags, 2 provisional" is data; "half the spec is still
     undecided, so building the billing flow now would be guessing" is an answer.
   - **Where the sources disagree.** `items/` records what the loop *believes* it finished; git records
     what actually landed. The script reports both, unreconciled, on purpose — a divergence is the most
     interesting thing on the page and it is yours to surface, not the script's to paper over.
   - **What to do next**, if asked. Anything parked is blocked on the human and outranks everything else.

4. **Lead with what is blocked on the reader.** If anything is parked, say so in the first sentence. A
   checkpoint that sits unanswered for a week is almost always one that was reported below a fold.

## Rules
- **Report, never repair.** If the spec is missing, the code map stale, or the backlog empty, say so and
  say what would fix it — do not run `ingest`, regenerate the map, or edit the backlog as a side effect.
  A question must not mutate the project; that is what makes it safe to ask at any time.
- **Never invent a number.** Every figure comes from the script or from a file you opened and can name.
  If you cannot source it, do not state it.
- **`missing` and `zero` are different answers.** "No spec" and "a spec with nothing in it" mean opposite
  things about a project; never collapse them.
- **A brownfield repo before `ingest` legitimately has no spec.** That is a state, not an error, and
  reporting it as a failure is how a correct project gets treated as broken.

## Output
Prose to the human, structured by the four faces the script gathers: **right now · what is intended · how
it connects · what is done · what is left**. No file is written. Nothing is queued.

## Route
Nothing. `status` is a **read**: it advances no node, claims no item, and mutates nothing. It is a side
door callable from anywhere, on the same footing as a question — if it produced work, the answer would
change the thing it was asked about.
