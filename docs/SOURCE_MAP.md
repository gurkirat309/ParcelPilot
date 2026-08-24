# SOURCE_MAP.md — sources, authority, and conflicts

The single most important reference in the repo. It defines which source wins
when they disagree, and enumerates every disagreement found by reading all 7
sources clause by clause. Every PDF is a single page; cites are `p.1 §N`.

---

## 1. Source inventory

| # | Filename | Type | Version | Status | Effective / Updated | Scope | Binds account |
|---|---|---|---|---|---|---|---|
| 01 | 01_Support_Policy_v3_CURRENT.pdf | Support policy | v3 | **CURRENT** | Eff. 1 May 2026 | Global | — |
| 02 | 02_Support_Policy_v2_DEPRECATED.pdf | Support policy | v2 | **DEPRECATED** | Eff. 1 Jan 2025; superseded by v3 1 May 2026 | Global | — |
| 03 | 03_Cancellation_and_Service_Credit_SOP_v4.pdf | SOP | v4 | **CURRENT** | Eff. 15 June 2026 | Global | — |
| 04 | 04_Product_Operations_Guide_and_Known_Issues.pdf | Ops guide / known issues | — | **CURRENT** (REFERENCE) | Updated 14 Aug 2026 | Global | — |
| 05 | 05_Northstar_Logistics_Enterprise_Agreement.pdf | Customer agreement | — | **CONTRACT** (ACTIVE) | Term 1 Jan–31 Dec 2026 | Account-specific | **ACCT-001** (Northstar) |
| 06 | 06_LumenWorks_Service_Agreement.pdf | Customer agreement | — | **CONTRACT** (ACTIVE) | Term 1 Mar 2026–28 Feb 2027 | Account-specific | **ACCT-002** (LumenWorks) |
| — | ParcelPilot_Assessment_Data.xlsx | Structured data | — | **DATA** | Snapshot 2026-08-16 11:00 IST | Global (row-scoped by account) | rows tagged per account |

All CURRENT docs and both contracts are effective/active at the snapshot
(2026-08-16). v2 is deprecated at snapshot.

---

## 2. Authority ranking (the precedence resolver)

Highest wins. This is deterministic and lives in code (`src/domain/precedence`),
never in a prompt.

1. **Customer-specific agreement** — *only when it binds the session's account.*
   Northstar agreement governs ACCT-001 only; LumenWorks agreement governs
   ACCT-002 only. A contract is invisible to every other account.
2. **Current global policy / SOP** — Support Policy **v3** (01) and Cancellation
   & Service Credit **SOP v4** (03).
3. **Product Operations Guide** (04) — capabilities, limits, known issues.
4. **Historical ticket resolutions** (`tickets.historical_resolution`) —
   **context only, never authoritative, never cited as the basis for an answer.**
5. **Deprecated docs** — Support Policy **v2** (02) — excluded from default
   retrieval; surfaced only for explicit "what changed between versions" queries.

**Reasoning.** (a) A signed agreement is the parties' specific bargain and the
v3 policy itself defers to it (01 §1: conflicts resolved "signed customer
agreement first, then the current support policy, then current product
documentation"). (b) Current global policy is the default floor. (c) The ops
guide is operational detail subordinate to policy. (d) Historical resolutions
are explicitly disclaimed as possibly-incorrect by both the README and 01 §1;
they capture what an agent once *said*, not what is *true*. (e) v2 is superseded
and self-labels "must not be used as current policy" (02).

Scope gate before ranking: a contract only enters the ranking for its own
account. For ACCT-003/004 (no contract) the top effective source is the current
global policy.

---

## 3. Conflict register

Quotes are short and page-cited. "Winner" is under the ranking in §2.

### C1 — Enterprise P1 first-response target
- **v3 (01 §3):** Enterprise P1 = "30 minutes, 24x7".
- **v2 (02, DEPRECATED):** Enterprise P1 = "1 hour".
- **Northstar contract (05 §1):** "P1: 15 minutes, 24x7" — explicitly
  "replace ParcelPilot's standard support-policy targets".
- **Winner:** ACCT-001 → **15 min, 24x7** (contract). Other Enterprise accounts
  (ACCT-004) → **30 min, 24x7** (v3). v2's 1 hour never applies (deprecated).

### C2 — Enterprise P2 / P3 targets
- **v3 (01 §3):** P2 = 2 hours; P3 = 1 business day.
- **v2 (02):** P2 = 4 hours; P3 = 2 business days.
- **Northstar (05 §1):** P2 = 1 hour; P3 = 8 business hours.
- **Winner:** ACCT-001 → contract (1 hour / 8 business hours). ACCT-004 → v3
  (2 hours / 1 business day). v2 excluded.

### C3 — Growth first-response targets (+ coverage)
- **v3 (01 §3):** Growth P1 = 2 business hours; P2 = 4 business hours;
  P3 = 2 business days.
- **v2 (02):** Growth P1 = 4 business hours; P2 = 1 business day;
  P3 = 3 business days.
- **LumenWorks (06 §1):** P1 = 2 business hours; P2 = 4 business hours;
  P3 = 2 business days; **"No weekend or after-hours support coverage."**
- **Winner:** ACCT-002 → contract. The P1/P2/P3 *numbers* happen to equal the v3
  Growth defaults, but the contract is still the governing source and it adds a
  **material coverage restriction (no weekend/after-hours)** absent from v3.
  Do not report v3 for LumenWorks even though the numbers coincide.

### C4 — Cancellation fee on a BOOKED, not-yet-picked-up shipment
- **SOP v4 (03 §1):** BOOKED not yet PICKED_UP — "No fee within 30 minutes of
  booking. After 30 minutes, charge INR 250 unless a customer agreement
  explicitly waives the cancellation fee."
- **Northstar (05 §2):** "Northstar may cancel any BOOKED shipment before pickup
  with no cancellation fee, regardless of how long ago the shipment was booked."
- **LumenWorks (06 §2):** "No special cancellation-fee waiver applies. Use the
  current ParcelPilot Cancellation & Service Credit SOP."
- **Historical (TKT-450, ACCT-001):** "Agent told customer a INR 250
  cancellation fee applied after 30 minutes."
- **Winner:** ACCT-001 → **no fee, ever, before pickup** (contract waiver). The
  TKT-450 historical resolution is **WRONG** — it applied the SOP default to an
  account whose contract waives the fee, and it was wrong even on its own date
  (2026-07-12, when both SOP v4 and the contract were in force). ACCT-002 and
  ACCT-003 (no waiver) → **INR 250 after 30 min, no fee within 30 min** (SOP).

### C5 — Failed-pickup service credit (amount + timing threshold)
- **SOP v4 default (03 §2):** eligible when pickup is "more than 2 hours past the
  end of the scheduled pickup window", carrier at fault, no customer-caused
  issue; credit = **lower of INR 500 or 10% of the shipment fee**.
- **LumenWorks (06 §3):** ">4 hours past ... end", carrier at fault, customer not
  at fault → **fixed INR 300**; "This clause replaces the default failed-pickup
  credit amount and timing threshold in the SOP."
- **Northstar (05 §3):** "Monthly aggregate service credits are capped at INR
  5,000. Unless this agreement states otherwise, the current ParcelPilot
  service-credit SOP applies." → uses the **SOP default per-incident formula**,
  plus a **monthly INR 5,000 aggregate cap**.
- **Winner:** ACCT-002 → LumenWorks (4h threshold, flat INR 300). ACCT-001 →
  SOP default formula, capped INR 5,000/month aggregate. ACCT-003/004 → SOP
  default. SOP approval rule (03 §3, any individual credit > INR 1,000 needs
  manager approval) still applies on top of all of these.

### C6 — Bulk-upload row limit
- **Product Ops Guide (04 §1):** Bulk Upload on Growth and Enterprise, "up to
  5,000 rows per CSV"; Standard not included.
- **Known issue KI-208 (04 §2):** intermittent failures above "approximately
  3,000 rows" even though "the supported product limit remains 5,000 rows";
  workaround = split below 3,000.
- **Historical (TKT-451, ACCT-002):** "Agent told customer Growth plan only
  supports 3,000 rows."
- **Winner:** Product Ops Guide — **supported limit is 5,000 rows**; 3,000 is a
  bug-workaround threshold (KI-208), not a plan cap. The TKT-451 historical
  resolution is **WRONG** and must not be cited; the correct answer explains the
  5,000 limit, KI-208, and the split-below-3,000 workaround.

### C7 — SwiftShip "still BOOKED after pickup" (known issue vs face-value data)
- **Product Ops Guide (04 §2, KI-211):** SwiftShip pickup webhooks "can arrive up
  to 20 minutes late ... verify the carrier status or wait through the known
  delay window" before telling a customer a pickup did not occur.
- **Order data:** a SwiftShip order can read `BOOKED` momentarily after physical
  pickup (e.g. TKT-504 / ORD-1001 context).
- **Winner / handling:** the ops guide governs interpretation — do not assert
  "not picked up" from `status=BOOKED` alone for SwiftShip within the delay
  window; verify. (Not a source-vs-source conflict so much as a data-trust rule.)

### C8 — Resolved issue KI-176 must not explain new incidents
- **Product Ops Guide (04 §3):** KI-176 resolved 18 July 2026; "Do not use this
  resolved issue to explain new incidents unless evidence specifically matches."
- **Handling:** never attribute a fresh incident to a resolved issue without a
  specific evidence match. (Trap against lazy pattern-matching.)

---

## 4. Rules needing a deterministic calculator

All in `src/domain/`, unit-tested. The model calls these; it never computes.

### CALC-1 — Cancellation fee
Inputs: `order.status`, `booked_at`, `cancellation_requested_at` (or the
requested time), snapshot, and the account's governing cancellation terms
(waiver? from precedence resolver).
Logic (SOP v4 §1, overridden per account):
- `DRAFT` → fee 0.
- `BOOKED` & not picked up:
  - if account contract waives fee (ACCT-001) → **0**, any elapsed time.
  - else elapsed = `cancellation_requested_at − booked_at`;
    ≤ 30 min → **0**; > 30 min → **INR 250**.
- `PICKED_UP` → not cancellable; direct to return-to-origin.
- `DELIVERED` → not cancellable.
Output: `{fee_inr, cancellable: bool, reason, route}`.

### CALC-2 — Failed-pickup service credit
Inputs: `pickup_window_end`, `pickup_actual_at` **or snapshot if still
unpicked**, `carrier_fault`, `customer_fault`, `shipment_fee_inr`, account
governing credit terms, and month-to-date credit total (for the cap).
Logic:
- Compute `delay = (pickup_actual_at or snapshot) − pickup_window_end`.
- Default (SOP v4 §2): eligible iff `delay > 2h AND carrier_fault AND NOT
  customer_fault`; amount = `min(500, round(0.10 * fee))`.
- LumenWorks (ACCT-002, 06 §3): eligible iff `delay > 4h AND carrier_fault AND
  NOT customer_fault`; amount = **300 flat**.
- Northstar (ACCT-001, 05 §3): default formula, then enforce **monthly aggregate
  ≤ INR 5,000** (clamp/deny the excess).
- Any individual credit **> INR 1,000 → manager-approval flag** (SOP v4 §3).
- If carrier fault / timing / customer fault is unknown → **do not promise**;
  return `needs_verification` (SOP v4 §3).
Output: `{eligible, amount_inr, needs_approval, needs_verification, basis}`.

### CALC-3 — First-response SLA target + breach
Inputs: account plan, governing contract targets (from precedence), severity
(P1/P2/P3), ticket `created_at` / `last_customer_message_at`, snapshot,
coverage calendar (24x7 vs business hours vs no-weekend/after-hours).
Logic: pick the governing target per C1–C3; compute elapsed against snapshot
within the applicable coverage calendar; flag breach (01 §4: state the breach,
recommend escalation). **Blocked on a business-hours definition — see OPEN
QUESTIONS.** 24x7 targets (Northstar P1) are computable now.
Output: `{target, coverage, elapsed, breached: bool}`.

### CALC-4 — Bulk-upload eligibility / limit advisory (lookup, not arithmetic)
Inputs: account plan, requested row count.
Logic (04 §1–§2): Standard → not available. Growth/Enterprise → supported to
5,000; if rows > ~3,000 attach the KI-208 advisory + split-below-3,000
workaround. Never quote "3,000-row plan limit".
Output: `{available, supported_max: 5000, ki208_advisory: bool}`.

---

## 5. Worked cases (from the order rows — for eval design, not hard-coded)

| Order | Acct | Situation | Correct result | Trap it defeats |
|---|---|---|---|---|
| ORD-1001 | 001 | BOOKED, cancel 120 min after booking | **No fee** (Northstar waiver) | SOP default INR 250 / TKT-450 |
| ORD-2001 | 002 | BOOKED, cancel 75 min after booking | **INR 250** (SOP; no waiver) | assuming all contracts waive |
| ORD-3001 | 003 | BOOKED, cancel 15 min after booking | **No fee** (within 30 min) | — |
| ORD-1002 | 001 | PICKED_UP, cancel after pickup | **Not cancellable**, return-to-origin | cancelling a picked-up order |
| ORD-4001 | 004 | DELIVERED | **Not cancellable** | — |
| ORD-2002 | 002 | Carrier-fault missed pickup; 4h30m past window end at snapshot, still BOOKED | **INR 300 flat** (LumenWorks, >4h met) | SOP default 2h/INR 240 |

Note ORD-2002 under the SOP default would be `min(500, 10%*2400=240)=240` at the
2h threshold; the LumenWorks contract overrides both threshold and amount → 300.

---

## 6. OPEN QUESTIONS FOR HUMAN REVIEW

1. **"Business hours" / "business day" are undefined.** No source states the
   working-day window, timezone, or holiday calendar. CALC-3 cannot compute
   non-24x7 targets without this. LumenWorks explicitly excludes weekends/
   after-hours but still doesn't define the hours. **Need a definition.**
2. **Timezone of workbook timestamps.** Order/ticket times are offset-naive; we
   assume Asia/Kolkata to match the snapshot. Confirm.
3. **What does `premium_support` govern?** ACCT-004 is Enterprise but
   `premium_support=False`, while ACCT-001 is True. v3 ties 24x7 to the
   Enterprise *plan*, not to this flag. Does `premium_support=False` remove 24x7
   for an Enterprise account, or is the flag informational? **Ambiguous.**
4. **Northstar monthly cap accounting basis.** "Monthly aggregate ... capped at
   INR 5,000" (05 §3) — calendar month? Rolling 30 days? Which timestamp
   (credit issued vs incident)? Assumed calendar month by incident date pending
   confirmation.
5. **Northstar P3 "8 business hours" vs its own 24x7 P1.** The contract mixes a
   24x7 P1 with business-hours P2/P3; the coverage calendar for Northstar P2/P3
   is not stated. Same blocker as (1).
6. **LumenWorks credit vs Northstar-style cap.** LumenWorks sets a flat per-
   incident credit but no aggregate cap; confirm there is intentionally no
   monthly ceiling for ACCT-002.
7. **Does the SOP's ">INR 1,000 manager approval" apply to contract-fixed
   credits?** LumenWorks' flat INR 300 is under the threshold so moot here, but
   confirm the approval rule rides on top of contract credit amounts generally.
