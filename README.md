# ParcelPilot AI Support Agent

An AI support agent over ParcelPilot's support corpus (6 PDFs + 1 workbook).
The corpus is deliberately imperfect — one deprecated policy, two overriding
customer agreements, and historical ticket resolutions that may be wrong.
Correctly resolving those conflicts is the point.

**[Watch the Loom Video Walkthrough](https://www.loom.com/share/28e502fe030947f48cd20cb9ace61aeb) | [Live Application](https://parcelpilot-keed.onrender.com/)**

> **Status:** scaffolding + data extraction/analysis phase. No application
> code yet. See `CLAUDE.md` for the rules and `docs/` for the analysis.

## Layout

```
data/raw/         source PDFs + workbook (not regenerable)
data/extracted/   extracted text/CSV (regenerable via scripts/extract.py)
docs/             DATA_SCHEMA.md, SOURCE_MAP.md, DECISIONS.md
scripts/          extract.py
src/              application code (later)
evals/            evaluation suite (later)
tests/            pytest suite
```

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
cp .env.example .env          # then fill in GROQ_API_KEY
```

## Build the data + run

```bash
python scripts/extract.py        # PDFs/XLSX -> data/extracted/
python -m src.data.db            # extracted CSVs -> data/parcelpilot.sqlite
python -m pytest -q              # 41 tests: calculators, precedence, access control, retrieval, API
uvicorn src.api.app:app --reload # serve the API on http://127.0.0.1:8000
```

Auth is mocked with bearer tokens (one per persona) — see `GET /health`:

| Token | Persona |
|---|---|
| `cust-acct-001` … `cust-acct-004` | customer, scoped to that account |
| `ops` | internal_ops (broad read) |

Example:

```bash
curl -s http://127.0.0.1:8000/chat -H "Authorization: Bearer cust-acct-001" \
  -H "Content-Type: application/json" \
  -d '{"message":"Can I cancel ORD-1001 without a fee? Explain why."}'
```

State-changing actions return a **pending proposal**; execute with
`POST /proposals/{id}/confirm`.

## Frontend (React chat console)

```bash
python scripts/gen_synthetic.py  # synthetic tickets for the ops board (analytics only)
python -m src.data.db            # re-ingest so they load
cd frontend && npm install && npm run build   # build -> frontend/dist
```

With `frontend/dist` present, the FastAPI server serves the whole app at
`http://127.0.0.1:8000` (one origin). The UI shows streamed tool traces, source
citations, confirmation cards, and (for `ops`) the proactive **Ops Board**. For
frontend dev with hot reload: `npm run dev` (proxies the API to :8000).

## Deploy (single container)

`Dockerfile` builds the React app, installs the backend, bakes the extracted
data + SQLite + embedding model, and serves everything. Deploy to Render/Railway
(see `render.yaml`); set `GROQ_API_KEY` and `GEMINI_API_KEY` as secrets.

## Key docs

- `CLAUDE.md` — architectural rules · `docs/SOURCE_MAP.md` — conflict register
- `docs/DATA_SCHEMA.md` · `docs/ARCHITECTURE_NOTE.md` · `docs/PRODUCT_NOTE.md`
- `docs/DECISIONS.md` — decision log · `docs/AI_TOOL_USAGE.md`

## Key docs

- `CLAUDE.md` — the non-negotiable architectural rules.
- `docs/SOURCE_MAP.md` — source inventory, authority ranking, conflict register.
- `docs/DATA_SCHEMA.md` — workbook schema, join graph, data-quality notes.
- `docs/DECISIONS.md` — append-only decision log.
