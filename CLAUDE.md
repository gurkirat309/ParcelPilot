# CLAUDE.md — ParcelPilot AI Support Agent

Auto-loaded every session. Read it, follow it, and **flag any instruction that
conflicts with a rule below** instead of silently complying.

## What this is

An AI support agent over a deliberately imperfect corpus (6 PDFs + 1 workbook)
for a logistics company, ParcelPilot. The grading target is **handling
conflicting / deprecated / non-authoritative sources correctly** — not
retrieval quality or UI polish.

## Stack

- Python 3.13, FastAPI, SQLite (stdlib `sqlite3`).
- LLM generation: **Gemini and/or Groq**, both wrapped behind `src/llm/client.py`
  (env `LLM_PROVIDER`, optional `LLM_FALLBACK_PROVIDER`). Default primary
  `gemini-3.7-flash`; fast fallback Groq `openai/gpt-oss-120b`.
- Retrieval: `rank_bm25` (lexical) + `fastembed` `BAAI/bge-small-en-v1.5`
  (local CPU embeddings). **No embeddings API — always local.**
- Frontend (later): React, streaming tool-call traces + confirmation cards.

## Non-negotiable rules

1. **Embeddings are ALWAYS local.** Never call an embeddings endpoint (no
   provider offers one we use — Groq has none, and the corpus is too small to
   justify a hosted one). Retrieval = BM25 + local `fastembed` embeddings.
   Free tiers are rate-limited: design for **few, fat tool calls**; cap the
   agent loop at **8 iterations**.
2. **All LLM access goes through `src/llm/client.py`.** No provider SDK calls
   anywhere else. Generation may use Gemini or Groq (env-selected); swapping or
   adding a provider must touch only that file.
3. **Time is frozen.** The snapshot timestamp from the workbook README sheet
   lives in config and is the ONLY "now". `datetime.now()` and `date.today()`
   are **banned repo-wide** — a test greps the tree and fails if either appears.
4. **Access control lives in the data layer.** `account_id` comes from the
   server-side session, never a model-settable tool parameter. A customer
   session physically cannot read another account's rows.
5. **State-changing tools never write on first call.** They return a
   `Proposal` (id, human-readable preview, status=pending). Execution happens
   only via a separate confirm endpoint. Enforced server-side, not by prompt.
6. **All money / fee / credit / SLA math is deterministic Python** in
   `src/domain/`, unit-tested. The model never does arithmetic and never
   decides eligibility — it calls a calculator and reports the result.
7. **Deprecated docs are excluded from default retrieval.** Retrievable only
   when a query explicitly asks what changed between versions.
8. **No agent frameworks.** Hand-write the tool-calling loop. No LangChain,
   LlamaIndex, CrewAI, etc. FastAPI + plain SDK calls only.
9. **Never hard-code** order IDs, account names, or answers from example
   questions. Everything is loaded and reasoned over at runtime.
10. **Never invent policy.** If it isn't in the sources, say so and escalate.

## Source precedence (deterministic resolver, highest → lowest)

1. Customer-specific agreement — **only** when it matches the session account.
2. Current global policy / SOP.
3. Product operations guide.
4. Historical ticket resolutions — **context only**, never authoritative,
   never cited as the basis for an answer.
5. Deprecated docs — excluded by default.

## Conventions

- Type hints on every function signature. Prefer `pydantic` models for
  structured data crossing boundaries.
- Tests: `pytest`, in `tests/`. Domain math and the precedence resolver get
  exhaustive unit tests. Add the `datetime`/`date` grep test early.
- Lint/format: `ruff`. Keep it clean.
- Append a `docs/DECISIONS.md` entry for every non-obvious choice.
- Small, single-purpose modules. `src/llm/`, `src/domain/`, `src/retrieval/`,
  `src/data/`, `src/agent/`, `src/api/`.

## Do NOT

- Call any embeddings API (Groq or otherwise).
- Put provider SDK calls outside `src/llm/client.py`.
- Use `datetime.now()` / `date.today()` / `time.time()` for business "now".
- Accept `account_id` as a model/tool-supplied parameter.
- Let a state-changing tool write on its first call.
- Let the model do arithmetic or decide eligibility.
- Retrieve deprecated docs by default.
- Add an agent framework.
- Hard-code IDs, names, or example answers.
- Invent policy content not present in the sources.
