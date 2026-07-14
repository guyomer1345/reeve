# 04 — Checkpoints (Space 4: the manual human-test gate)

## MVP scope **[DECIDED]**
Structured **manual** checkpoints surfaced through the website. Flow:

> orchestrator hits a checkpoint → blocks (waits on the bus) → posts to the website WHAT to verify and
> HOW (doc links, screenshots of where a setting lives, step-by-step) → optionally a screen-share so
> Claude gives live feedback → human reports pass/fail + notes → bus delivers the verdict →
> orchestrator resumes.

## Block/resume mechanism **[DECIDED — D90, empirically verified]**
A checkpoint is a **durable park boundary**, not a live in-session wait (nothing inside Claude can self-wake — no
background-exit re-invoke, no hook that wakes an idle model). The orchestrator writes the graceful handoff +
verdict-request to disk and **yields**; the verdict lands on the local bus into a durable **append-only inbox**
(D91 correlation); resume is **`claude --resume <id> -p "<verdict>"`** — the verdict rides as an *authoritative
prompt* (a `SessionStart` hook only re-points to durable state; hook-injected context is under-weighted), cold-
starting from `handoff.md` + `git log` if the session store is gone. Restart trigger = **manual in MVP** (a console
prompt) → a **local relaunch runner** later. **Not** a hook exit-code trick (a `Stop` hook exiting 2 forces
*continue*, not pause). While parked, the orchestrator **interleaves** to the next independent ticket (D91).

**The away-channel for a bounded question (D93 conversation corollary).** A checkpoint is also how the orchestrator
asks the *away* human a bounded question — it parks with the request, the human answers async via the bus, it
resumes. Open-ended new-feature **dialogue** is *not* a checkpoint; it's a terminal activity (the live `discuss`
session). The bus carries only bounded clarifications + `intake` requests, never a real-time chat (the loop is a
batch consumer — see `05`).

## Motivating example (user)
Setting up a Polar account: each time Claude said to change a setting, the human had to go find exactly
where it lives in Polar's docs/UI. The workflow should instead surface the doc location / a screenshot,
or take a screen-share and give live feedback.

## To close **[OPEN]**
- **What a checkpoint IS** (the data model) — awaiting more examples from Guy.
- What triggers a checkpoint (who decides one is needed). *(kind=qa resolved — the plan's `human-qa`-gated
  acceptance criteria, D30; demo/setup triggers still open.)*
- Which help features are MVP (doc links / screenshots / screen-share / live feedback).

## Out of scope (designed-for, not built) **[DEFERRED]**
Automated testing; test-from-anywhere (run-while-away → test env → Cloudflare tunnel → phone ping);
the paid device/QA platform.
