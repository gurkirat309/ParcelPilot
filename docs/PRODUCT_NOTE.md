# Product Note — ParcelPilot AI Support Agent

## Which additional client problem — we addressed **both**, in depth

### Problem 2: Trust & Reliability (the spine of the system)
The whole architecture is built around not being confidently wrong:

- A **deterministic precedence resolver** decides which source governs every
  answer (own contract → current policy/SOP → product guide → historical =
  context-only → deprecated = excluded). Conflicts resolve the same way every time.
- **Money, credits, and SLAs are computed in code**, never by the model, and every
  result is returned **with a citation** (file/page/section/quote).
- **Historical ticket resolutions are never cited** — the two planted wrong
  answers (Northstar's "INR 250 fee", the "3,000-row limit") are overridden by
  the governing source, and the agent says so.
- **Honest uncertainty**: when fault/timing is unknown, or a business-hours SLA
  target is undefined in the sources, the system says "indeterminate" and
  **escalates** instead of inventing a number.
- **Access control in the data layer**: a customer can't see another account's
  data even if the model is coaxed — scope comes from the session, not the prompt.

### Problem 1: Proactive Issue Detection (the internal Ops Board)
An internal-only dashboard (`/ops/signals`, gated to `internal_ops`) that surfaces:

- **SLA watch** — every open ticket's first-response target and breach status,
  breaches first (e.g. Northstar's P1 outage already breached at snapshot).
- **Issue clusters** — tickets grouped by known-issue signature (KI-208 bulk
  upload, KI-211 SwiftShip), with counts and affected accounts.
- **Multi-customer issues** — the same signature hitting ≥2 accounts at once.
- **Spikes** — a surge in the 24h before the snapshot vs baseline.

Because the real corpus has only 7 tickets, we added a **clearly-labelled
synthetic ticket set** (analytics-only, `is_synthetic=1`, never reaching the
customer agent or the authority layer) so clustering/spike detection has real
signal. This is exactly the "add more data" the brief invites, kept isolated from
the authority base that Problem 2 depends on.

## Anything else we'd build for ParcelPilot (prioritised)

Prioritised by *protect-the-core → close-the-loop → scale*, with the reason each
matters. Rough effort in brackets.

### Tier 1 — protect the core promise ("never confidently wrong")
1. **Answer-level eval harness + CI gate** [S]. A graded question bank (the trap
   cases + precedence/edge cases) that fails the build on any regression. *Why it
   matters most:* the entire value proposition is trustworthiness; without
   automated evals, a prompt tweak or model swap could silently reintroduce a
   confidently-wrong answer. This is the cheapest, highest-leverage safeguard.
2. **Confirmed-action write-back + immutable audit log** [M]. Today actions are
   mocked and proposals live in memory. Production needs real ticket/escalation
   execution with a durable, tamper-evident audit trail. *Why:* trust requires
   accountability — every automated action must be attributable and reversible.
3. **Business-hours / holiday calendar in config** [S]. Makes the non-24×7 SLA
   targets that are currently "indeterminate" actually computable. *Why:* it's the
   single biggest correctness gap the sources leave open, and it converts a large
   class of "escalate to a human" into confident answers.

### Tier 2 — close the detection → action loop (proactive value)
4. **One-click actions from the Ops Board** [M]. Turn a detected cluster (e.g.
   KI-208 across 3 accounts) into a bulk escalation, a status-page incident, or a
   proactive customer notification. *Why:* converts detection into deflected
   inbound tickets — the clearest operational ROI.
5. **Credit ledger + monthly-cap enforcement** [M]. Persist issued credits so
   Northstar's ₹5,000 monthly aggregate cap is enforced across real history
   (today the clamp works but month-to-date is 0 at runtime), with finance-facing
   spend analytics. *Why:* correctness of contractual caps + cost visibility.
6. **Answer feedback loop** [S]. Thumbs up/down + "was this the governing source?"
   on each answer, feeding a human-review queue and the eval set. *Why:* turns real
   usage into a compounding quality signal and labelled data.

### Tier 3 — scale to a real corpus and operate reliably
7. **Retrieval hardening** [M]. Section-aware chunking, a cross-encoder reranker,
   inline citation highlighting, and automated version/effective-dating of docs.
   *Why:* the assessment corpus is ~24 chunks; production has hundreds of
   docs and many versions where naive hybrid search degrades.
8. **Provider observability + smart routing** [M]. Per-answer trace logging,
   latency/cost/rate-limit dashboards, and cost-/health-aware routing across Groq
   and Gemini. *Why:* keeps the agent fast and cheap under real load (the 503 we
   hit on a free tier is exactly this class of problem).
9. **Real auth + per-role tooling + tenant-isolation tests** [M]. Replace mock
   bearer tokens with SSO, scope tools by role, and add automated cross-account
   leakage tests to CI. *Why:* the access-control property is real today but the
   identity layer and its regression tests are not.
10. **Multi-turn memory + proactive follow-ups** [M]. Session summarisation and
    scheduled follow-up tasks (e.g. "check whether KI-208 is resolved for these 3
    accounts"). *Why:* moves from reactive Q&A toward an assistant that follows
    through.

## What we intentionally left out

- **Real authentication** — mocked with bearer tokens (per the brief's allowance);
  the security *property* (scope from the session) is real, the identity provider
  isn't.
- **Token-level streaming** — we stream tool steps, not tokens; the tool trace is
  the informative part and stays uniform across providers.
- **A hosted embeddings API / vector DB** — unjustified at ~24 chunks.
- **Write-back of confirmed actions to real systems** — actions are mocked
  locally (also per the brief); the proposal→confirm gate is fully real.
- **Multi-turn memory beyond the session** — conversations are per-session.

## One metric

**Grounded-resolution rate**: the share of answered queries that (a) cite a
governing source and (b) match the deterministic resolver's verdict — with a hard
sub-goal that the **incorrect-authority rate is ~0** (never basing an answer on a
deprecated doc or a historical resolution). It directly measures the thing that
kills adoption: confidently wrong answers. Its natural companion is the
**appropriate-escalation rate** (uncertain cases escalated rather than guessed).
