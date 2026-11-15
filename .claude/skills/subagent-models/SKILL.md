---
name: subagent-models
description: Pick the right model for every subagent you spawn in CropLytics work (haiku for mechanical work, sonnet for most builds and research, opus only for hard cross-cutting design). Use before any Agent/Task call, when planning parallel agents, or when a session is near its usage limit.
---

# Subagent models

Every Agent call sets `model` explicitly. Never let a subagent inherit Opus by default. The team hit the 5-hour usage limit once with every agent on Opus.

## Choose by the job

| Model | Use it for | CropLytics examples |
|---|---|---|
| `haiku` | Mechanical, well-specified work with a clear done-check | rerun `build_api.py` or `run_all.py`; download or cache refreshes; smoke-test the live site; extract text from a transcript; move or copy files; run checks and report counts |
| `sonnet` | Most implementation, web research and writing (the default) | a new API route plus schema and checks; a data fetcher for a public API; estimate builders; a frontend panel from a given spec; research with citations; docs |
| `opus` | Hard, cross-cutting or ambiguous work only | a design that spans engine, API and frontend; reconciling conflicting data sources; tricky algorithms (engine scoring, detectors); synthesis where judgement decides the outcome; reviewing a risky merge |

Rules of thumb:
- If the brief can list exact steps and a pass/fail check, use **haiku**.
- If it needs reading code and writing new code against a known contract, use **sonnet**.
- If you'd want a senior engineer to make the call, use **opus**. Say why in one line in the brief.
- Research: use **sonnet**. Only use opus when the synthesis is the deliverable, such as a ranked strategy.
- Don't upgrade a model to compensate for a vague brief; fix the brief.

## Also

- One agent per coherent chunk, with disjoint file ownership. Use a git worktree when two agents would touch the same files.
- Work is pushed to main automatically once it's green; the user asked for this. Pushing is allowed for the coordinating session, or for an agent whose brief says so, only through the gate:
  - stage explicit paths;
  - pass `check_api.py` ALL PASS for backend changes;
  - keep the engine checks unchanged;
  - pass the frontend typecheck and `VITE_API_BASE=/api npm run build`;
  - `git pull --rebase` first; never force-push.

  Agents sharing a checkout leave committing to the coordinator.
- Running agents can't change model. Apply this to new spawns.
