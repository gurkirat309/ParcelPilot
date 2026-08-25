"""Generate a comprehensive interview-prep study guide PDF for the ParcelPilot
AI Support Agent project. Pure reportlab (Platypus). Run:

    python scripts/make_study_guide.py
"""

from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    HRFlowable, ListFlowable, ListItem, PageBreak, Paragraph, SimpleDocTemplate,
    Spacer, Table, TableStyle,
)

OUT = Path(__file__).resolve().parents[1] / "docs" / "ParcelPilot_Study_Guide.pdf"

# --- fonts: prefer Windows TrueType for full Unicode (INR, arrows, ticks) ------
FONTS = Path("C:/Windows/Fonts")
def _reg(name, file):
    try:
        pdfmetrics.registerFont(TTFont(name, str(FONTS / file)))
        return True
    except Exception:
        return False

BODY = "Body" if _reg("Body", "segoeui.ttf") else "Helvetica"
BOLD = "Bold" if _reg("Bold", "segoeuib.ttf") else "Helvetica-Bold"
ITAL = "Ital" if _reg("Ital", "segoeuii.ttf") else "Helvetica-Oblique"
MONO = "Mono" if _reg("Mono", "consola.ttf") else "Courier"
MONOB = "MonoB" if _reg("MonoB", "consolab.ttf") else "Courier-Bold"

# palette
NAVY = colors.HexColor("#0f1e3d")
BLUE = colors.HexColor("#2f6df6")
ACC = colors.HexColor("#6b4cff")
INK = colors.HexColor("#1c2333")
MUT = colors.HexColor("#5b667e")
LINE = colors.HexColor("#d6deea")
SOFT = colors.HexColor("#f2f5fb")
GOODBG = colors.HexColor("#e7f7ef")
WARNBG = colors.HexColor("#fdf0e3")
BADBG = colors.HexColor("#fde7ec")
CODEBG = colors.HexColor("#0f1420")
CODEFG = colors.HexColor("#e6ecf7")

styles = getSampleStyleSheet()


def S(name, **kw):
    kw.setdefault("fontName", BODY)
    return ParagraphStyle(name, parent=styles["Normal"], **kw)


ST = {
    "title": S("t", fontName=BOLD, fontSize=26, textColor=NAVY, leading=30, spaceAfter=4),
    "sub": S("s", fontName=BODY, fontSize=12, textColor=MUT, leading=16, spaceAfter=2),
    "h1": S("h1", fontName=BOLD, fontSize=16, textColor=NAVY, leading=20, spaceBefore=14, spaceAfter=4),
    "h2": S("h2", fontName=BOLD, fontSize=12.5, textColor=BLUE, leading=16, spaceBefore=10, spaceAfter=3),
    "body": S("b", fontSize=9.6, textColor=INK, leading=14, spaceAfter=5, alignment=TA_LEFT),
    "bul": S("bu", fontSize=9.6, textColor=INK, leading=13.5),
    "small": S("sm", fontSize=8.4, textColor=MUT, leading=11),
    "cell": S("c", fontSize=8.6, textColor=INK, leading=11.5),
    "cellb": S("cb", fontName=BOLD, fontSize=8.6, textColor=NAVY, leading=11.5),
    "cellh": S("ch", fontName=BOLD, fontSize=8.6, textColor=colors.white, leading=11.5),
    "code": S("cd", fontName=MONO, fontSize=8.2, textColor=CODEFG, leading=12),
    "q": S("q", fontName=BOLD, fontSize=9.8, textColor=NAVY, leading=13, spaceBefore=7, spaceAfter=1),
}

story = []


def h1(t): story.append(Paragraph(t, ST["h1"])); story.append(HRFlowable(width="100%", thickness=1.4, color=BLUE, spaceAfter=6))
def h2(t): story.append(Paragraph(t, ST["h2"]))
def p(t): story.append(Paragraph(t, ST["body"]))
def small(t): story.append(Paragraph(t, ST["small"]))
def sp(h=6): story.append(Spacer(1, h))


def bullets(items):
    li = [ListItem(Paragraph(x, ST["bul"]), leftIndent=10, value="•") for x in items]
    story.append(ListFlowable(li, bulletType="bullet", start="•", leftIndent=8,
                              bulletColor=BLUE, bulletFontSize=8, spaceAfter=5))


def code(lines):
    txt = "<br/>".join(l.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                       .replace(" ", "&nbsp;") for l in lines)
    t = Table([[Paragraph(txt, ST["code"])]], colWidths=[170 * mm])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), CODEBG),
                           ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                           ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                           ("ROUNDEDCORNERS", [4, 4, 4, 4])]))
    story.append(t); sp(6)


def callout(tag, text, bg):
    inner = Paragraph(f'<font name="{BOLD}">{tag}</font>&nbsp;&nbsp;{text}', ST["cell"])
    t = Table([[inner]], colWidths=[170 * mm])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), bg),
                           ("LEFTPADDING", (0, 0), (-1, -1), 9), ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                           ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                           ("LINEBEFORE", (0, 0), (0, -1), 3, BLUE)]))
    story.append(t); sp(6)


def table(header, rows, widths):
    data = [[Paragraph(c, ST["cellh"]) for c in header]]
    for r in rows:
        data.append([Paragraph(c, ST["cell"]) for c in r])
    t = Table(data, colWidths=[w * mm for w in widths], repeatRows=1)
    style = [("BACKGROUND", (0, 0), (-1, 0), NAVY),
             ("GRID", (0, 0), (-1, -1), 0.5, LINE),
             ("VALIGN", (0, 0), (-1, -1), "TOP"),
             ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
             ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]
    for i in range(1, len(data)):
        if i % 2 == 0:
            style.append(("BACKGROUND", (0, i), (-1, i), SOFT))
    t.setStyle(TableStyle(style))
    story.append(t); sp(7)


# ============================================================ COVER
story.append(Spacer(1, 40))
story.append(Paragraph("ParcelPilot AI Support Agent", ST["title"]))
story.append(Paragraph("Interview Study Guide &mdash; complete project reference", ST["sub"]))
story.append(HRFlowable(width="100%", thickness=2, color=ACC, spaceBefore=8, spaceAfter=10))
p("An AI customer-support + internal-ops agent over a <b>deliberately imperfect</b> corpus "
  "(6 PDFs + a workbook) for a B2B logistics company. Built as a CalQuity AI-Engineer "
  "take-home. The graded core is <b>handling conflicting, deprecated, and wrong sources "
  "correctly</b> &mdash; not retrieval or UI polish.")
callout("ELEVATOR PITCH",
        "One agent, two personas (customer / internal-ops). A deterministic <b>source-precedence "
        "resolver</b> and <b>deterministic calculators</b> decide every fee, credit and SLA &mdash; the "
        "LLM orchestrates and explains but never does the math or decides eligibility. Every answer "
        "cites its governing source; historical/deprecated sources are never used as authority. "
        "Stack: FastAPI + SQLite + hybrid BM25/local-embeddings retrieval + a hand-written tool loop "
        "on Groq (Gemini fallback), React front end, single-container hosting.", SOFT)
h2("The two planted traps (the heart of the assessment)")
table(["Trap", "Wrong historical answer", "Correct answer", "Why"],
      [["Cancellation<br/>(TKT-450, Northstar)", "\u201cINR 250 fee applies after 30 min\u201d",
        "<b>No fee</b>, ever, before pickup",
        "Northstar\u2019s contract waives the fee; contract &gt; SOP. Wrong even on its own date."],
       ["Bulk upload<br/>(TKT-451, LumenWorks)", "\u201cGrowth plan caps at 3,000 rows\u201d",
        "<b>5,000</b> supported; 3,000 is a bug workaround",
        "Product limit is 5,000; 3,000 is the KI-208 workaround threshold, not a plan cap."]],
      [34, 44, 42, 50])
small("Snapshot / frozen clock: <b>2026-08-16 11:00 Asia/Kolkata</b>. Currency: INR. "
      "Live: https://parcelpilot-keed.onrender.com &nbsp;|&nbsp; Repo: gurkirat309/ParcelPilot")
story.append(PageBreak())

# ============================================================ 1. PROBLEM
h1("1. Problem &amp; what is graded")
p("ParcelPilot is a B2B logistics platform. Customers ask about entitlements, contract terms, "
  "cancellations, service credits, and SLAs, and report product issues. The support corpus is "
  "<b>intentionally imperfect</b>: one policy is deprecated, two customer agreements override "
  "general policy, and some historical ticket resolutions are wrong.")
bullets([
    "<b>Graded core:</b> deliberately handling source authority / conflicts / uncertainty &mdash; "
    "not retrieval quality or UI.",
    "Must load and reason at runtime &mdash; <b>no hard-coded IDs or answers</b> (they test with other records).",
    "Two example questions: cancel ORD-1001 without a fee (Northstar); 3h-late carrier-fault credit.",
    "Two extra client problems &mdash; we addressed <b>both</b>: Problem 1 (proactive detection) and "
    "Problem 2 (trust &amp; reliability).",
])

h1("2. The 10 non-negotiable rules (architecture invariants)")
table(["#", "Rule"],
      [["1", "Embeddings are ALWAYS local (fastembed). Design for few, fat tool calls; agent loop capped at 8 iterations."],
       ["2", "All LLM access goes through src/llm/client.py. No provider SDK calls anywhere else."],
       ["3", "Time is frozen: the workbook snapshot is the only \u2018now\u2019. datetime.now()/date.today() banned; a test greps for them."],
       ["4", "Access control lives in the data layer. account_id comes from the session, never a model-set parameter."],
       ["5", "State-changing tools never write on first call. They return a pending Proposal; execution is a separate confirm step."],
       ["6", "All money/fee/credit/SLA math is deterministic Python, unit-tested. The model never does arithmetic or decides eligibility."],
       ["7", "Deprecated docs excluded from default retrieval; retrievable only for \u2018what changed\u2019 queries."],
       ["8", "No agent frameworks. Hand-written tool-calling loop. FastAPI + plain SDK calls only."],
       ["9", "Never hard-code order IDs, account names, or example answers."],
       ["10", "Never invent policy. If it is not in the sources, say so and escalate."]],
      [8, 162])

# ============================================================ 3. ARCHITECTURE
h1("3. Architecture &amp; request flow")
code([
    "React SPA  --HTTP / SSE-->  FastAPI",
    "                             |- auth: bearer token -> Session (role, account_id server-side)",
    "                             |- agent loop (hand-written, <=8 iters, streams tool steps)",
    "                             |     |- LLM client  (Groq primary | Gemini fallback)",
    "                             |     '- tools:",
    "                             |          - search_documents  -> retrieval (BM25 + fastembed)",
    "                             |          - get_order/account/ticket -> repository (scope-enforced)",
    "                             |          - calc_* -> deterministic domain calculators",
    "                             |          - create_escalation/update_ticket/... -> proposals",
    "                             '- /ops/signals -> Problem-1 analytics",
])
p("<b>Layering (src/):</b> config (frozen clock) - domain (policy+citations, precedence, calculators) - "
  "data (sqlite ingest, repository) - retrieval (chunks, hybrid index) - llm (client) - "
  "agent (tools, loop, proposals) - ops (signals) - api (app, auth).")
bullets([
    "<b>Backend:</b> Python 3.13, FastAPI, SQLite (stdlib).",
    "<b>Retrieval:</b> rank_bm25 + fastembed BAAI/bge-small-en-v1.5 (local CPU, ~24 chunks).",
    "<b>LLM:</b> Groq openai/gpt-oss-120b primary; Gemini gemini-3.7-flash fallback; one client module.",
    "<b>Frontend:</b> React + Vite; streamed tool traces, confirmation cards, ops board.",
    "<b>Hosting:</b> single container (FastAPI serves built React); Dockerfile + render.yaml.",
])

story.append(PageBreak())

# ============================================================ 4. PRECEDENCE
h1("4. Source precedence &amp; the conflict register (THE CORE)")
p("A deterministic resolver ranks sources; the same ranking gates retrieval and resolves the terms "
  "the calculators use. <b>Contracts are scope-gated</b> &mdash; an account only ever sees its own contract.")
table(["Tier", "Source", "Role in an answer"],
      [["1 (highest)", "Customer\u2019s OWN agreement", "Overrides policy, but only for its own account."],
       ["2", "Current policy / SOP (v3, SOP v4)", "The default floor when no contract applies."],
       ["3", "Product Operations Guide", "Capabilities, limits, known issues (KI-208, KI-211)."],
       ["4", "Historical ticket resolutions", "CONTEXT ONLY. May be wrong. NEVER cited as a basis."],
       ["5 (lowest)", "Deprecated docs (Policy v2)", "Excluded by default; only for \u2018what changed\u2019 queries."]],
      [22, 58, 90])
h2("Sources at a glance")
table(["File", "Type", "Status", "Effective", "Binds"],
      [["01 Support Policy v3", "policy", "CURRENT", "2026-05-01", "global"],
       ["02 Support Policy v2", "policy", "DEPRECATED", "2025-01-01", "global (excluded)"],
       ["03 Cancellation &amp; Credit SOP v4", "sop", "CURRENT", "2026-06-15", "global"],
       ["04 Product Ops Guide + Known Issues", "guide", "CURRENT", "2026-08-14", "global"],
       ["05 Northstar Enterprise Agreement", "contract", "ACTIVE", "2026 term", "ACCT-001"],
       ["06 LumenWorks Service Agreement", "contract", "ACTIVE", "2026-27 term", "ACCT-002"],
       ["ParcelPilot_Assessment_Data.xlsx", "data", "DATA", "snapshot", "row-scoped"]],
      [55, 20, 26, 26, 43])

h2("Conflict register (what each source says &amp; who wins)")
table(["Topic", "Default / policy", "Contract override", "Winner"],
      [["Cancellation fee", "No fee &lt;=30min; else INR 250 (SOP v4)",
        "Northstar: no fee ever before pickup", "Northstar\u2192 no fee; others\u2192 SOP"],
       ["Failed-pickup credit", "&gt;2h + carrier fault \u2192 min(INR 500, 10% fee)",
        "LumenWorks: &gt;4h \u2192 flat INR 300 (replaces both)", "Per account (see calculators)"],
       ["Credit cap", "individual &gt; INR 1,000 needs manager approval",
        "Northstar: INR 5,000 monthly aggregate cap", "Both apply on top"],
       ["Enterprise P1 SLA", "v3: 30 min 24x7 (v2 was 1h)",
        "Northstar: 15 min 24x7", "ACCT-001\u219215m; ACCT-004\u2192v3 30m"],
       ["Growth SLA + coverage", "v3: P1 2 business hrs...",
        "LumenWorks: same numbers + NO weekend/after-hours", "Contract governs (coverage differs)"],
       ["Bulk upload limit", "5,000 rows (Growth/Enterprise); KI-208 &gt;~3,000",
        "\u2014", "Product guide; 5,000 not 3,000"]],
      [30, 48, 48, 44])
callout("KEY INSIGHT", "LumenWorks\u2019 SLA numbers equal the v3 Growth defaults, yet the <b>contract "
        "still governs</b> because it adds a coverage restriction (no weekend / after-hours). "
        "\u2018Numbers match\u2019 is not \u2018same source\u2019.", WARNBG)

story.append(PageBreak())

# ============================================================ 5. DATA
h1("5. Data model &amp; the frozen clock")
p("Workbook \u2192 SQLite (typed). 4 accounts, 6 orders, 7 real tickets (+10 synthetic, analytics-only). "
  "account_id is the hub; every scoped query filters by the session account.")
table(["Table", "Key columns", "Notes"],
      [["accounts", "account_id PK, plan, contract_file, premium_support",
        "ACCT-001 Northstar/Ent, 002 LumenWorks/Growth, 003 Beacon/Std, 004 Axis/Ent"],
       ["orders", "order_id PK, account_id FK, status, booked_at, pickup_window_end, carrier_fault, shipment_fee_inr",
        "status BOOKED/PICKED_UP/DELIVERED; pickup_actual_at null while unpicked"],
       ["tickets", "ticket_id PK, account_id FK, status, historical_resolution, is_synthetic",
        "historical_resolution may be WRONG; is_synthetic=1 never reaches the agent"]],
      [22, 78, 70])
bullets([
    "<b>Frozen clock:</b> SNAPSHOT_AT = 2026-08-16 11:00 IST lives in config and is the only \u2018now\u2019. "
    "A test greps src/scripts/evals for datetime.now(/date.today(/time.time( and fails if found.",
    "<b>Data-quality traps handled:</b> customer_fault has zero variance (still read per-row); "
    "pickup delay for unpicked orders is measured to the snapshot; timestamps assumed Asia/Kolkata.",
])

# ============================================================ 6. CALCULATORS
h1("6. Deterministic calculators (src/domain) &mdash; Rule 6")
p("Pure functions: primitives in, a typed result (with citations) out. The tool layer fetches the "
  "DB row, resolves precedence, then calls these. The model reports the result &mdash; it never computes.")
h2("CALC-1 Cancellation fee")
bullets(["DRAFT\u2192 free. PICKED_UP\u2192 not cancellable (return-to-origin). DELIVERED\u2192 not cancellable.",
         "BOOKED: contract waiver \u2192 INR 0 any time; else &lt;=30min \u2192 0, &gt;30min \u2192 INR 250."])
h2("CALC-2 Failed-pickup service credit")
bullets(["delay = (pickup_actual_at or snapshot) - pickup_window_end.",
         "Default (SOP): delay&gt;2h AND carrier_fault AND NOT customer_fault \u2192 min(INR 500, 10% fee).",
         "LumenWorks: delay&gt;4h \u2192 flat INR 300 (replaces threshold &amp; amount).",
         "Northstar: SOP formula + INR 5,000 monthly aggregate cap (clamped).",
         "Individual credit &gt; INR 1,000 \u2192 manager-approval flag. Unknown fault/timing \u2192 needs_verification (don\u2019t promise)."])
h2("CALC-3 First-response SLA + breach")
bullets(["Only clock-time 24x7 targets are exactly computable (e.g. Northstar P1 15 min).",
         "Business-hours / business-day targets \u2192 <b>computable=False (indeterminate)</b>: the docs never "
         "define a business calendar, so we don\u2019t guess &mdash; a deliberate trust signal."])
h2("CALC-4 Bulk-upload advisory")
bullets(["Standard\u2192 not available. Growth/Enterprise\u2192 supported to 5,000; &gt;~3,000 attaches the KI-208 advisory + split workaround."])
callout("WHY DETERMINISTIC", "Money/eligibility in tested Python (not the LLM) is what makes answers "
        "auditable and stops \u2018confidently wrong\u2019 arithmetic. Policy thresholds are transcribed into "
        "cited dataclasses (policy.py) &mdash; not invented, and the raw text stays the authority the agent quotes.", SOFT)

story.append(PageBreak())

# ============================================================ 7. RETRIEVAL / LLM / ACCESS
h1("7. Retrieval, LLM client, access control")
h2("Retrieval (src/retrieval)")
bullets([
    "PDFs \u2192 page-marked text \u2192 section chunks (~24) tagged with tier/status/bound-account.",
    "Hybrid score = 0.5*minmax(cosine of fastembed) + 0.5*minmax(BM25). No embeddings API.",
    "Gating: deprecated excluded unless the query asks \u2018what changed / v2\u2019; contract chunks visible "
    "only to their account (or internal_ops).",
])
h2("LLM client (src/llm/client.py) &mdash; the ONLY SDK caller")
bullets([
    "Neutral messages/tools adapted to each provider; returns text and/or tool calls.",
    "Groq primary (clean tool calling). Gemini fallback &mdash; a 3.x \u2018thinking\u2019 model that requires "
    "replaying a thought_signature on tool-call history (client captures/replays it).",
    "Automatic fallback on primary error &mdash; a live-demo safety net.",
])
h2("Access control (src/data/repository.py) &mdash; Rule 4")
bullets([
    "Session(role, account_id) from a bearer token (auth.py). Customer pinned to own account.",
    "Another account\u2019s order/ticket returns None (not an error that leaks existence).",
    "The model can pass an order_id but never an account_id &mdash; it cannot widen scope.",
])
code(["# demo tokens", "cust-acct-001..004  -> customer, that account", "ops -> internal_ops (broad read)"])

# ============================================================ 8. AGENT / PROPOSALS
h1("8. Agent loop &amp; proposal gating")
bullets([
    "Hand-written loop (Rule 8): call LLM with tool schemas; run tool calls; feed results back; "
    "repeat until a text answer or the 8-iteration cap.",
    "iter_agent is a generator \u2192 /chat/stream emits SSE (tool_call / tool_result / final) for live traces.",
    "System prompt states the rules, but <b>enforcement is in code</b> (repository, calculators, proposal store).",
    "State-changing tools return a <b>pending</b> Proposal; execution only via POST /proposals/{id}/confirm, "
    "scoped to the owning account (Rule 5). In-memory store (mock actions, per the brief).",
])

# ============================================================ 9. PROBLEM 1
h1("9. Problem 1 &mdash; proactive detection (Ops Board)")
p("Internal-only analytics (/ops/signals) over ALL tickets (real + synthetic), measured at the snapshot.")
bullets([
    "<b>SLA watch:</b> every open ticket\u2019s target + breach (24x7 exact; business-hours indeterminate).",
    "<b>Clusters:</b> tickets grouped by known-issue signature (KI-208 bulk upload, KI-211 SwiftShip).",
    "<b>Multi-customer:</b> the same signature across &gt;=2 accounts at once.",
    "<b>Spikes:</b> surge in the 24h before the snapshot vs baseline.",
    "Synthetic tickets (is_synthetic=1) add signal but are ISOLATED &mdash; the customer agent reads real data only.",
])

# ============================================================ 10. API / FE / DEPLOY / TESTS
h1("10. API, frontend, hosting, tests")
table(["Endpoint", "Purpose"],
      [["GET /health", "status + active provider + key presence (debug)"],
       ["GET /me", "session role + account_id"],
       ["POST /chat", "run agent (collected result)"],
       ["POST /chat/stream", "SSE: streamed tool_call / tool_result / final"],
       ["GET /ops/signals", "Problem-1 dashboard (internal only)"],
       ["GET /proposals; POST /proposals/{id}/confirm|cancel", "list / execute / drop a pending action"]],
      [66, 104])
bullets([
    "<b>Frontend:</b> React/Vite; persona switch (=token), streamed tool-trace chips (expandable JSON+citation), "
    "markdown answers, confirmation cards, ops board.",
    "<b>Hosting:</b> multi-stage Dockerfile builds React, bakes extracted data + SQLite + embedding model "
    "(offline runtime), serves everything on one origin; render.yaml blueprint.",
    "<b>Tests:</b> 46 pytest (calculators, precedence, access-control isolation, retrieval gating, ops signals, "
    "API auth/proposals) + the datetime grep test; ruff clean.",
])
callout("DEPLOY GOTCHA", "If the app answers with a Gemini 503, LLM_PROVIDER is not set to groq on the host "
        "(it defaults there) or GROQ_API_KEY is missing. Set LLM_PROVIDER=groq + both keys; /health should "
        "show llm_provider=groq, groq_key_set=true.", WARNBG)

story.append(PageBreak())

# ============================================================ 11. DECISIONS
h1("11. Key decisions &amp; trade-offs (be ready to defend these)")
table(["Decision", "Why", "Trade-off / rejected"],
      [["Deterministic calculators + precedence resolver",
        "Model must not do math or decide eligibility \u2192 auditable, testable, not confidently wrong.",
        "More code vs letting the LLM reason freely (rejected: unverifiable)."],
       ["Local embeddings (no API)", "Corpus ~24 chunks: local is faster, offline, container-safe.",
        "~130MB model in image vs a hosted embedder (no benefit at this size)."],
       ["Groq primary, Gemini fallback", "Groq clean tool calls; Gemini 3.x hit 503/429 + needs signature replay.",
        "Reversible via one env var; fallback is the demo safety net."],
       ["No agent framework", "Transparent, few deps, full control of the loop; shows fundamentals.",
        "Hand-written vs LangChain conveniences."],
       ["Access control in data layer", "A customer cannot reach another account even if the model is coaxed.",
        "Slightly more plumbing than prompt-only (which is unsafe)."],
       ["Frozen clock + grep test", "Reproducible, snapshot-consistent time-based answers.",
        "Bans wall clock repo-wide."],
       ["Synthetic tickets isolated by flag", "Demonstrate Problem 1 without polluting the authority base.",
        "Extra column + dual read path."]],
      [42, 66, 62])

# ============================================================ 12. LIMITATIONS + ROADMAP
h1("12. Known limitations &amp; \u2018what I\u2019d build next\u2019")
h2("Documented limitations (not hidden)")
bullets([
    "Business-hours SLA targets are \u2018indeterminate\u2019 (source docs never define the calendar).",
    "Northstar monthly cap logic is tested but month-to-date is not persisted (no credit ledger).",
    "Proposals + auth are in-memory / mock (allowed by the brief).",
])
h2("Prioritised roadmap (protect core \u2192 close loop \u2192 scale)")
bullets([
    "<b>Tier 1:</b> answer-level eval harness + CI gate; real action write-back + audit log; business-hours calendar.",
    "<b>Tier 2:</b> one-click actions from the Ops Board; credit ledger + cap enforcement; answer feedback loop.",
    "<b>Tier 3:</b> retrieval reranking + doc versioning; provider observability + smart routing; real auth + "
    "isolation tests; multi-turn memory.",
])
callout("ONE METRIC", "<b>Grounded-resolution rate</b> &mdash; share of answers that cite a governing source AND "
        "match the deterministic resolver, with a hard sub-goal of ~0 incorrect-authority rate (never basing an "
        "answer on a deprecated/historical source). Companion: appropriate-escalation rate.", GOODBG)

story.append(PageBreak())

# ============================================================ 13. INTERVIEW Q&A
h1("13. Likely interview questions &amp; crisp answers")
qa = [
    ("How do you stop the agent being confidently wrong?",
     "Four layers: a deterministic precedence resolver picks the governing source; deterministic calculators "
     "(not the LLM) do all money/SLA math; every answer cites its source; and historical/deprecated sources are "
     "never used as authority. Unknown inputs \u2192 escalate, not guess."),
    ("Why no agent framework?",
     "A hand-written loop is transparent, has few dependencies, and gives full control over tool schemas, the "
     "8-iteration cap, and streaming. It also demonstrates fundamentals rather than hiding them."),
    ("How is access control enforced, and why not in the prompt?",
     "In the repository (data layer). The Session\u2019s account_id comes from a server-side bearer token; a "
     "customer query is physically pinned to that account and another account\u2019s row returns None. Prompt-only "
     "control is bypassable; data-layer control is not."),
    ("Why local embeddings instead of an embeddings API?",
     "The corpus is ~24 chunks, so embedding quality differences are negligible; local fastembed adds no latency, "
     "no keys, no rate limits, and works offline inside the container. Groq has no embeddings endpoint anyway."),
    ("Why Groq primary over Gemini?",
     "Empirical: Groq gpt-oss-120b did clean tool round-trips first try; Gemini 3.x flash hit 503/429 under load "
     "and, being a thinking model, rejected tool history missing a thought_signature. Gemini is a wired-up fallback."),
    ("Explain the frozen clock and why it matters.",
     "The dataset is a snapshot; the workbook README timestamp is the only \u2018now\u2019. Using the wall clock would "
     "make time-based answers (SLA breach, cancellation window) non-reproducible, so datetime.now/date.today are "
     "banned and a test greps for them."),
    ("How do the two contracts override policy without leaking across accounts?",
     "The precedence resolver scope-gates a contract to its bound account_id before ranking. Northstar\u2019s waiver "
     "applies only to ACCT-001; ACCT-003 asking the same question falls through to the SOP."),
    ("LumenWorks\u2019 SLA numbers equal v3 &mdash; why does the contract still win?",
     "Because it adds a material coverage restriction (no weekend/after-hours). Matching numbers is not the same "
     "source; citing v3 would drop that clause."),
    ("How is \u2018confirmation before actions\u2019 actually enforced?",
     "State-changing tools return a pending Proposal and never write on the first call. Execution is a separate "
     "server endpoint (/proposals/{id}/confirm) scoped to the owner &mdash; enforced in code, not by asking the model."),
    ("How does proactive detection avoid corrupting the authority data?",
     "Synthetic tickets carry is_synthetic=1. The repository (what the agent sees) reads real rows only; the ops "
     "signals module reads real+synthetic for analytics. Analytics never becomes authority."),
    ("What happens when fault or timing is unknown?",
     "The credit calculator returns needs_verification and the agent refuses to promise a credit &mdash; it explains "
     "what\u2019s missing and offers to escalate. Same philosophy as the indeterminate SLA case."),
    ("What would break at 100x the data, and what would you change?",
     "Naive hybrid search degrades \u2192 add section-aware chunking + a reranker + doc versioning. SQLite is fine for "
     "moderate scale. The precedence/calculator core is unaffected. Add an eval harness before any model change."),
    ("Walk me through a multi-step query.",
     "\u2018Can I cancel ORD-1001 without a fee?\u2019 \u2192 search_documents (policy) + get_order (scoped) + "
     "calc_cancellation_fee (resolves Northstar\u2019s waiver) \u2192 a cited answer, all in one streamed turn."),
]
for q, a in qa:
    story.append(Paragraph("Q. " + q, ST["q"]))
    story.append(Paragraph("A. " + a, ST["body"]))

sp(4)
small("Generated for interview preparation. All facts reflect the implemented project "
      "(46 tests passing, deployed on Render). See docs/SOURCE_MAP.md, ARCHITECTURE_NOTE.md, "
      "PRODUCT_NOTE.md, DECISIONS.md in the repo for the source-of-truth detail.")


# ---- page numbers ----
def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont(BODY, 8)
    canvas.setFillColor(MUT)
    canvas.drawString(20 * mm, 12 * mm, "ParcelPilot AI Support Agent \u2014 Study Guide")
    canvas.drawRightString(190 * mm, 12 * mm, f"Page {doc.page}")
    canvas.setStrokeColor(LINE)
    canvas.line(20 * mm, 15 * mm, 190 * mm, 15 * mm)
    canvas.restoreState()


doc = SimpleDocTemplate(str(OUT), pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm,
                        topMargin=18 * mm, bottomMargin=20 * mm,
                        title="ParcelPilot AI Support Agent - Study Guide",
                        author="ParcelPilot project")
doc.build(story, onFirstPage=footer, onLaterPages=footer)
print("Wrote", OUT)
