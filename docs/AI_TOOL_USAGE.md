# AI Tool Usage

- **Claude Code (Anthropic)** was used as the primary development assistant
  throughout: reading and analysing the source pack, writing the conflict
  register / data schema, scaffolding the codebase, implementing the backend
  (domain calculators, precedence resolver, retrieval, agent loop, API) and the
  React frontend, writing the pytest suite, and driving in-browser verification.
- All architectural rules and non-negotiable constraints (Groq/Gemini providers,
  local embeddings, frozen clock, data-layer access control, propose-then-confirm)
  were **human-specified**; the assistant implemented and tested against them, and
  flagged conflicts (e.g. the deprecated Groq model, the embeddings-API question)
  for a human decision rather than deciding silently.
- Every non-obvious choice is recorded in `docs/DECISIONS.md`; the assistant was
  asked to keep that log as it worked.
- **The runtime agent** uses **Groq** (`openai/gpt-oss-120b`) as the primary LLM
  and **Google Gemini** (`gemini-3.7-flash`) as an automatic fallback, both behind
  `src/llm/client.py`. Retrieval embeddings run locally via `fastembed`
  (`BAAI/bge-small-en-v1.5`) — no embeddings API is used.
