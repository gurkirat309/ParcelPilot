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

1. **Draft-reply + suggested-action from the Ops Board** — turn a detected
   cluster (e.g. KI-208 across 3 accounts) into a one-click proactive escalation
   or status-page note. Highest leverage: closes the loop from detection to action.
2. **Credit-ledger persistence** — track issued credits so Northstar's INR 5,000
   monthly aggregate cap is enforced across real history (today it's computed but
   month-to-date is not persisted).
3. **A defined business-hours calendar** (config) so non-24×7 SLA targets become
   computable — the single biggest gap the sources leave open.
4. **Answer-level evals** — a graded question bank (incl. the trap cases) run in
   CI to catch precedence regressions.
5. **Real auth + per-role tooling** and a DB-backed proposal/audit log.

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
