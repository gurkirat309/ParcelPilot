# Decision Log

Append-only. Newest at the bottom. One entry per non-obvious choice, with the
reasoning that would otherwise be lost.

Format:

```
## YYYY-MM-DD — <short title>
**Context:** why this came up
**Decision:** what we chose
**Reasoning:** why, and what we rejected
```

---

## 2026-08-25 — Project root at C:\CalQuity
**Context:** The brief references `data/raw/` with 7 named files. Those live
under `C:\CalQuity\data\raw`, not the session's primary working dir
(`C:\animated_site`, an unrelated project).
**Decision:** Treat `C:\CalQuity` as the ParcelPilot project root; scaffold
everything there.
**Reasoning:** The data location is authoritative for where the project lives.
Keeping ParcelPilot isolated from the animated-site repo avoids cross-contamination.

## 2026-08-25 — Isolated virtualenv for extraction
**Context:** System Python 3.13.8 has none of the required libs (pdfplumber,
openpyxl, pandas).
**Decision:** Create a project-local `.venv` and install from `requirements.txt`.
**Reasoning:** Keeps the assessment reproducible and avoids polluting global
Python. `.venv/` is gitignored.

## 2026-08-25 — Extraction preserves page boundaries and profiles the workbook
**Context:** Downstream retrieval needs page-level authority metadata and we
must characterise data-quality problems.
**Decision:** `scripts/extract.py` writes `--- PAGE n ---` markers per PDF page
and, per XLSX sheet, a CSV plus a printed profile (dtypes, nulls, low-cardinality
uniques, 5 sample rows). It asserts exactly 7 correctly-named raw files first.
**Reasoning:** Page cites are required throughout SOURCE_MAP.md; the profile is
the raw material for DATA_SCHEMA.md's data-quality section.

## 2026-08-25 — Frozen clock = 2026-08-16 11:00 Asia/Kolkata
**Context:** Rule 3 bans `datetime.now()`/`date.today()`; the only "now" is the
workbook README snapshot.
**Decision:** Canonical snapshot is `2026-08-16T11:00:00+05:30`. It goes in
config as the sole clock; delay/SLA math measures against it.
**Reasoning:** Read directly from README sheet. Order/ticket timestamps are
offset-naive, so we treat them as Asia/Kolkata to match (flagged as OPEN QUESTION).

## 2026-08-25 — Both closed-ticket historical resolutions are WRONG (by design)
**Context:** Deciding how much to trust `tickets.historical_resolution`.
**Decision:** Treat historical resolutions as context-only tier-4 sources and
never cite them. Recorded both errors in SOURCE_MAP conflict register C4 and C6.
**Reasoning:** TKT-450 applied the SOP's INR 250 fee to Northstar, whose contract
waives it (wrong even on its 2026-07-12 date). TKT-451 called 3,000 rows a
"Growth plan limit"; the product limit is 5,000 and 3,000 is only the KI-208
workaround threshold. Correctly overriding these is the graded core, so they are
documented explicitly rather than silently retrieved.

## 2026-08-25 — Contract scope-gating before precedence ranking
**Context:** A customer agreement outranks global policy, but only for its own
account.
**Decision:** The precedence resolver first scope-gates a contract to its binding
`account_id` (via `accounts.contract_file`), then ranks. LumenWorks' numbers
coincide with v3 Growth defaults but the contract still governs ACCT-002 because
it adds a coverage restriction (no weekend/after-hours).
**Reasoning:** Prevents one account's contract leaking into another's answers and
prevents "numbers match, so cite policy" errors.

## 2026-08-25 — Scope locked: both personas, both client problems, hosted
**Context:** After reading the official assessment PDF (CalQuity AI Engineer JD +
ParcelPilot assessment), confirmed alignment and chose scope. The brief requires
only ONE chatbot and ONE additional problem; we deliberately go broader.
**Decision:**
- Build **both personas**: `customer` (own-account scoped) and `internal_ops`
  (broader read + ops tooling).
- Address **both** additional problems **in depth**: Problem 2 (trust &
  reliability — already the spine of our architecture) and Problem 1 (proactive
  issue detection — an internal_ops board: SLA-breach detection, duplicate-issue
  / same-KI grouping, multi-customer issue surfacing).
- **Host** the app as a single container (Render/Railway): FastAPI serving the
  built React app + local fastembed model.
**Reasoning:** Maximises signal on the two graded axes and wins the "highly
preferred" hosted-link credit. Accepted trade-off: larger surface area across the
remaining two phases; mitigated by finishing the deterministic engine + tests in
phase 2 before any UI, and by reusing the phase-1 analysis docs for the required
Architecture/Product notes.

## 2026-08-25 — Synthetic tickets permitted for Problem 1 demonstrability
**Context:** Problem 1 (proactive detection: spikes, multi-customer issues) is
hard to demonstrate with only 7 tickets. The brief explicitly allows adding data
("add more data if you think it makes for a more complete solution").
**Decision:** For the internal_ops proactive board, generate a clearly-labelled
synthetic ticket set (kept separate from `data/raw`, flagged as synthetic) that
amplifies existing real signals — e.g. more KI-208 bulk-upload tickets across
multiple accounts, more SwiftShip KI-211 reports, and SLA-approaching P1s — so
clustering/spike detection has something real to find. Real corpus stays the
authority base; synthetic data is analytics-only and never a policy source.
**Reasoning:** Keeps Problem 1 honest and demonstrable without contaminating the
authority/precedence layer that Problem 2 depends on.

## 2026-08-25 — LLM provider: Gemini primary + Groq fallback; embeddings stay local
**Context:** Groq deprecated `llama-3.3-70b-versatile` and `llama-3.1-8b-instant`
on 2026-06-17 (free/dev tiers). User has a Gemini API key and asked whether a
free embeddings API is worth using. This revisits self-imposed Rule 1.
**Decision:**
- **Generation** is now provider-agnostic behind `src/llm/client.py`, env-selected
  (`LLM_PROVIDER`, `LLM_FALLBACK_PROVIDER`). Default primary **`gemini-3.7-flash`**
  (newest stable Flash, tool calling, ~1,500 req/day + ~1M TPM free tier, stable
  IDs); fast fallback **Groq `openai/gpt-oss-120b`** (Groq's recommended
  tool-calling replacement for the deprecated Llama 3.3).
- **Embeddings stay LOCAL** (`fastembed` bge-small). A free embeddings API is
  explicitly rejected: the corpus is ~30–60 chunks, so a hosted embedder adds a
  key, per-query latency, rate-limit surface, and a container network dependency
  for zero measurable retrieval benefit. Local is faster, offline, and container-safe.
**Reasoning:** Gemini's free tier is more generous and its model IDs more stable
than Groq's (which just churned our model), so it's the safer primary for a graded
live demo; Groq remains a fast fallback. The two-provider switch is a resilience
story for the Architecture Note. This relaxes the "Groq only" half of Rule 1 but
*reaffirms* the "embeddings are local" half. No conflict with the official brief,
whose "use only the supplied data pack" governs the knowledge base, not the model.

## 2026-08-25 — Phase 2 build: engine, retrieval, agent, API
**Context:** Built the deterministic engine + retrieval + agent loop + API.
**Decisions & reasoning:**
- **Cited structured policy (`src/domain/policy.py`).** Calculators need
  machine-readable thresholds; hard-coding raw policy prose would risk Rule 10.
  Resolution: transcribe each threshold/amount into a dataclass carrying a
  `Citation` (file, page, section, quote). Math logic is code; parameters are
  cited transcriptions; the raw doc text (via retrieval) stays what the agent
  quotes to users. No order IDs or example answers are hard-coded.
- **Access control in the repository, not the model (Rule 4).** `Session(role,
  account_id)` comes from a server-side bearer token (`src/api/auth.py`). Customer
  queries pin to their own account; another account's row returns None (no
  existence leak). The model never sees or sets account_id.
- **SLA business-hours honesty.** CALC-3 computes only clock-time 24x7 targets
  exactly (e.g. Northstar P1); business-hours/-day targets return
  `computable=False` with a reason instead of guessing a calendar. Matches
  SOURCE_MAP OPEN QUESTION #1 and doubles as a trust signal.
- **Provider flipped to Groq-primary (empirical).** Live tests: Groq
  `gpt-oss-120b` did a clean tool round-trip first try; `gemini-3.7-flash` hit 503
  and 429 AND, as a thinking model, rejected tool history missing a
  `thought_signature`. Fixed the client to capture/replay that signature (opaque
  `ToolCall.signature`) so Gemini works as fallback, and set LLM_PROVIDER=groq /
  fallback=gemini for demo reliability. Reversible via env. (Supersedes the
  Gemini-primary note above.)
- **Proposals in a process-wide in-memory store.** Mock actions per the brief;
  pending on create, execute only via POST /proposals/{id}/confirm, scoped to the
  owning account. Fine for a single-process assessment server; DB-backing later.
**State:** 41 tests green, ruff clean. Example + both trap questions answer
correctly end-to-end. Remaining for Phase 3: streaming, React UI, Problem 1 board
(+ synthetic tickets), hosting, Architecture/Product notes, demo video.

## 2026-08-25 — Phase 3 build: streaming, React UI, ops board, hosting
**Context:** Delivered the surface + both client problems + hosting + notes.
**Decisions & reasoning:**
- **SSE step-streaming.** `iter_agent` is the core loop as an event generator;
  `/chat/stream` emits `tool_call`/`tool_result`/`final`. Streaming *which tool
  runs* is the valuable signal and is provider-uniform; token-streaming wasn't
  worth provider-specific plumbing.
- **Problem 1 kept out of the authority layer.** Synthetic tickets live behind
  `is_synthetic=1`; the repository (customer/internal agent) reads real data only,
  while `src/ops/signals.py` reads real+synthetic for analytics. Signals =
  deterministic issue classification + SLA watch + clusters + spikes +
  multi-customer, measured against the frozen snapshot. SLA breaches shown only
  where exactly computable (24x7); business-hours targets marked indeterminate.
- **Single-container hosting.** FastAPI serves the built React `dist` (mounted
  after API routes). `Dockerfile` bakes extracted data + SQLite + the embedding
  model so runtime is offline and fast; `render.yaml` for turnkey deploy.
- **React SPA** with persona switch, streamed tool-trace chips, markdown answers,
  confirmation cards, and the ops board. Verified live in-browser: cancellation
  trap (no fee, contract cited), bulk-upload trap (5,000 not 3,000), ops board
  spikes/clusters/SLA breaches, and propose→confirm escalation.
- **Written deliverables** added: `ARCHITECTURE_NOTE.md`, `PRODUCT_NOTE.md`
  (chose BOTH problems; metric = grounded-resolution rate with ~0 incorrect-
  authority rate), `AI_TOOL_USAGE.md`.
**State:** 46 tests green, ruff clean, frontend builds, full stack verified in the
browser. Remaining: user records the ~5-min demo video and deploys to their host.

