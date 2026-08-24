# Architecture Note — ParcelPilot AI Support Agent

## Overview

One agent, two personas (`customer`, `internal_ops`), over a deliberately
imperfect corpus (6 PDFs + a workbook). FastAPI backend + React frontend, served
as a single container. LLM generation is provider-agnostic (Groq primary, Gemini
fallback); retrieval embeddings are 100% local. The design goal is **trustworthy
answers under conflicting sources**, not retrieval or UI polish.

```
React SPA ──HTTP/SSE──> FastAPI
                          ├─ auth (bearer token → Session; account_id server-side)
                          ├─ agent loop (hand-written, ≤8 iters)
                          │    ├─ LLM client  (Groq | Gemini, one interface)
                          │    └─ tools ──> retrieval (BM25 + fastembed, authority-gated)
                          │              ├─ repository (SQLite, scope-enforced)
                          │              ├─ domain calculators (deterministic $/SLA)
                          │              └─ proposals (pending → confirm)
                          └─ ops signals (Problem 1 analytics)
```

## Agent design

- **Hand-written tool-calling loop** (no framework, Rule 8). Each turn: call the
  LLM with the tool schemas; if it returns tool calls, execute them, append
  results, and loop; otherwise return the text. Capped at **8 iterations** to
  respect free-tier rate limits.
- **Provider-agnostic** behind `src/llm/client.py` (the only module that imports
  an SDK). A neutral message/tool representation is adapted to each provider.
  Groq is primary (empirically clean tool calling); Gemini is an automatic
  fallback (its 3.x "thinking" models require replaying a `thought_signature`,
  which the client handles).
- **Streaming**: the loop is also an event generator; `/chat/stream` emits SSE
  (`tool_call` / `tool_result` / `final`) so the UI shows each tool live.
- **System prompt** encodes the precedence ranking and the hard rules (use tools,
  never guess, never do the math, never cite historical/deprecated sources,
  propose-then-confirm). But **enforcement is in code, not the prompt** — the
  prompt is a hint; the guarantees live in the tools/repository/proposal layer.

## Tool design

Four categories (the brief requires ≥3):

1. **Document search** — hybrid retrieval with authority metadata.
2. **Scoped structured lookups** — `get_order/account/ticket`, `list_tickets`.
3. **Deterministic calculators** — cancellation fee, service credit, SLA,
   bulk-upload. The model calls these; it never computes or decides eligibility.
4. **Proposal-gated actions** — `create_escalation`, `update_ticket`,
   `create_followup_task`, each returning a *pending* proposal.

Design choices: tools take **ids and judgments** (order_id, severity), never an
`account_id` a customer could set — scope comes from the session. Calculator
results carry **citations** (file/page/section/quote) so answers are grounded.
Tool results are compact JSON ("few, fat calls").

## Document & structured-data handling

- **Documents**: PDFs are extracted with page markers, chunked by section, and
  tagged with their source's authority tier + status + (for contracts) the bound
  account. Retrieval is **BM25 + local `fastembed` (bge-small)** with min-max
  hybrid scoring. **No embeddings API** — the corpus is tiny (~24 chunks), so a
  hosted embedder would add latency/keys/limits for no benefit.
- **Structured data**: the workbook is ingested into **SQLite** with typed casts.
  Access control lives in the **repository** (Rule 4): a customer `Session` is
  physically pinned to its own `account_id`; another account's row returns
  `None`, never an error that leaks existence. `internal_ops` gets broad read.
- **Frozen clock**: the workbook snapshot (`2026-08-16 11:00 IST`) is the only
  "now"; `datetime.now()`/`date.today()` are banned and a test greps for them.

## Source reliability & conflict handling (the core)

A deterministic **precedence resolver** ranks sources:

1. the caller's **own** customer agreement (scope-gated to that account),
2. current global policy / SOP (Support Policy v3, SOP v4),
3. product operations guide,
4. historical ticket resolutions — **context only, never cited**,
5. deprecated docs (Policy v2) — **excluded** unless the query asks what changed.

This is applied in two places: retrieval **gates** deprecated/contract chunks,
and the calculators **resolve effective terms** through the same ranking. The two
planted traps are handled correctly and provably (see the conflict register in
`SOURCE_MAP.md` and the tests): Northstar's contract waives the cancellation fee
that a historical ticket wrongly charged; the real bulk-upload limit is 5,000
(the "3,000" historical answer was a KI-208 workaround threshold, not a plan cap).
When inputs are unknown or a target is indeterminate, the agent **escalates**
rather than guessing.

## Major technical trade-offs

- **Local embeddings over a hosted API** — reliability/latency/offline hosting
  win at this corpus size; the cost is a ~130 MB model in the image (pre-warmed
  at build).
- **Groq primary, Gemini fallback** — chosen on empirical reliability during the
  build (Gemini 3.x hit 503/429 and needed signature replay). Reversible by one
  env var; the fallback is a live-demo safety net.
- **Structured policy transcribed with citations** — calculators need
  machine-readable thresholds; hard-coding raw prose would risk "inventing
  policy," so each parameter is a cited transcription and the raw text (via
  retrieval) stays the authority the agent quotes.
- **In-memory proposals & mock auth** — appropriate for a single-process
  assessment; a DB-backed store and real auth are the obvious hardening.
- **Step-level streaming, not token-level** — showing which *tool* runs is the
  valuable signal and works uniformly across providers; token streaming was not
  worth provider-specific complexity.
