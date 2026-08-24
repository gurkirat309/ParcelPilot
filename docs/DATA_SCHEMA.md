# DATA_SCHEMA.md — ParcelPilot workbook

**Dataset snapshot timestamp (the ONLY "now"): `2026-08-16T11:00:00+05:30` (2026-08-16 11:00 Asia/Kolkata).**

Source: `README` sheet of `ParcelPilot_Assessment_Data.xlsx`. Currency is **INR**
throughout. Dataset is synthetic (hiring assessment). The README also warns:
*"Some historical ticket resolutions may be incorrect. Treat them as historical
context, not policy authority."* — this drives the whole precedence design.

All timestamps in the workbook are **naive strings without an offset**. We treat
them as Asia/Kolkata (matching the snapshot). See OPEN QUESTIONS in SOURCE_MAP.md.

---

## Sheets overview

The workbook has 4 sheets: `README` (metadata), `accounts`, `orders`, `tickets`.

### `README` (metadata, not tabular)
Key–value layout, not a real table. pandas reads the title as the header, so the
two "columns" are `'ParcelPilot AI Agent Assessment - Structured Data'` and
`'Unnamed: 1'`. The meaningful content is 4 key/value pairs:

| Key | Value |
|---|---|
| Dataset snapshot | `2026-08-16 11:00 Asia/Kolkata` |
| Currency | `INR` |
| Notes | Synthetic dataset created for a hiring assessment. |
| Important | Some historical ticket resolutions may be incorrect. Treat them as historical context, not policy authority. |

**Ingestion note:** parse this sheet as key/value, not as a dataframe. The
snapshot value must be lifted into config as the frozen clock.

---

### `accounts` (4 rows) — one row per customer account

| Column | Type | Notes |
|---|---|---|
| `account_id` | str, PK | Format `ACCT-00N`. Values: ACCT-001…004. |
| `account_name` | str | Axis Labs, Beacon Retail, LumenWorks, Northstar Logistics. |
| `plan` | enum | `Enterprise` \| `Growth` \| `Standard`. |
| `status` | enum | Only value present: `active`. |
| `csm` | str | Customer success manager (Arjun Rao, Neha Kapoor, Priya Mehta). |
| `contract_file` | str \| null | Filename of the binding agreement PDF, or null if none. Null for ACCT-003, ACCT-004 (no custom agreement — expected, not an orphan). |
| `premium_support` | bool | True only for ACCT-001. **Ambiguous** — see below and OPEN QUESTIONS. |
| `notes` | str | Free text describing the support arrangement. |

Rows:

| account_id | name | plan | contract_file | premium_support |
|---|---|---|---|---|
| ACCT-001 | Northstar Logistics | Enterprise | 05_Northstar_Logistics_Enterprise_Agreement.pdf | True |
| ACCT-002 | LumenWorks | Growth | 06_LumenWorks_Service_Agreement.pdf | False |
| ACCT-003 | Beacon Retail | Standard | (null) | False |
| ACCT-004 | Axis Labs | Enterprise | (null) | False |

`contract_file` is the join key from an account to its governing agreement PDF.
It matches the raw filenames exactly, so it can drive the precedence resolver's
"does this account have an overriding contract?" check.

---

### `orders` (6 rows) — one row per shipment

| Column | Type | Notes |
|---|---|---|
| `order_id` | str, PK | Format `ORD-NNNN`. First digit tracks account (1→ACCT-001, 2→ACCT-002, 3→003, 4→004). |
| `account_id` | str, FK → accounts | |
| `carrier` | enum | BlueDart Pro, RoadRunner, SwiftShip. |
| `status` | enum | `BOOKED` \| `PICKED_UP` \| `DELIVERED`. (SOP also mentions `DRAFT`; none present.) |
| `booked_at` | datetime str | |
| `pickup_window_start` | datetime str | |
| `pickup_window_end` | datetime str | Basis for pickup-delay math. |
| `pickup_actual_at` | datetime str \| null | Null while not yet picked up (all 4 BOOKED rows). Present for PICKED_UP/DELIVERED. |
| `shipment_fee_inr` | int | 1200…5100. Basis for percentage-based credit. |
| `carrier_fault` | bool | |
| `customer_fault` | bool | **Only value present: False** (no variance) — the calculator must still read it, never assume. |
| `cancellation_requested_at` | datetime str \| null | Null when no cancellation was requested (ORD-2002, ORD-4001). |
| `notes` | str | Free text. |

Full rows (key fields):

| order | acct | status | booked_at | window_end | actual | fee | carrier_fault | cancel_req |
|---|---|---|---|---|---|---|---|---|
| ORD-1001 | 001 | BOOKED | 08-16 09:00 | 08-16 11:30 | — | 4200 | F | 08-16 11:00 |
| ORD-1002 | 001 | PICKED_UP | 08-16 08:10 | 08-16 10:00 | 08-16 09:35 | 5100 | F | 08-16 10:20 |
| ORD-2001 | 002 | BOOKED | 08-16 09:00 | 08-16 12:00 | — | 1800 | F | 08-16 10:15 |
| ORD-2002 | 002 | BOOKED | 08-16 04:30 | 08-16 06:30 | — | 2400 | **T** | — |
| ORD-3001 | 003 | BOOKED | 08-16 10:25 | 08-16 13:00 | — | 1200 | F | 08-16 10:40 |
| ORD-4001 | 004 | DELIVERED | 08-14 14:00 | 08-15 10:00 | 08-15 09:20 | 3600 | F | — |

These rows are engineered to exercise the calculators — see SOURCE_MAP.md
"Worked cases".

---

### `tickets` (7 rows) — one row per support ticket

| Column | Type | Notes |
|---|---|---|
| `ticket_id` | str, PK | Format `TKT-NNN`. |
| `account_id` | str, FK → accounts | |
| `created_at` | datetime str | |
| `status` | enum | `open` \| `closed`. |
| `subject` | str | |
| `description` | str | |
| `channel` | enum | `chat` \| `email`. |
| `assigned_to` | str | Maya \| Rohit. |
| `last_customer_message_at` | datetime str | For SLA first-response reasoning. |
| `historical_resolution` | str \| null | **CONTEXT ONLY. May be WRONG.** Non-null only on the 2 closed tickets — both are incorrect (see SOURCE_MAP conflict register). |

Rows:

| ticket | acct | status | subject | historical_resolution |
|---|---|---|---|---|
| TKT-501 | 001 | open | All shipment creation is failing (HTTP 500) | (null) |
| TKT-502 | 002 | open | Bulk upload fails for 4,200-row CSV | (null) |
| TKT-503 | 003 | open | How do we change the billing contact? | (null) |
| TKT-504 | 001 | open | SwiftShip order still shows BOOKED after pickup | (null) |
| TKT-505 | 004 | open | Possible API key exposure | (null) |
| TKT-450 | 001 | closed | Cancellation fee after 30 minutes | "Agent told customer a INR 250 cancellation fee applied after 30 minutes." **← WRONG for Northstar** |
| TKT-451 | 002 | closed | Bulk upload fails for large CSV | "Agent told customer Growth plan only supports 3,000 rows." **← WRONG** |

---

## Join graph

```
accounts (account_id, PK)
   │  1─┐
   │    ├──< orders.account_id   (each order belongs to one account)
   │    └──< tickets.account_id  (each ticket belongs to one account)
   │
   └── contract_file ──→ data/raw/<agreement>.pdf   (0..1 governing contract)
                          ACCT-001 → Northstar agreement
                          ACCT-002 → LumenWorks agreement
                          ACCT-003, ACCT-004 → none

tickets ↔ orders: NO explicit foreign key. Related only implicitly via
account_id + subject/description text (e.g. TKT-504 clearly concerns a
SwiftShip BOOKED order for ACCT-001, matching ORD-1001; TKT-502 concerns a
4,200-row bulk upload for ACCT-002). Any linkage must be inferred, never assumed.
```

`account_id` is the hub. **Every scoped query filters by the session
`account_id`** (Rule 4). No cross-account foreign keys exist to leak through.

---

## Data-quality problems noticed

1. **`customer_fault` has zero variance** (always False across all 6 orders).
   Calculators must still read the field per-row rather than hard-coding the
   assumption, or a future non-False row silently produces a wrong credit.
2. **`pickup_actual_at` is null for all BOOKED orders.** Pickup-delay math for
   still-unpicked orders must measure against the frozen snapshot
   (`now − pickup_window_end`), not against a null actual time.
3. **README is not tabular.** Auto-parsing yields junk column names
   (`Unnamed: 1`); the snapshot must be lifted by key, not by position.
4. **Timezone is implicit.** Only the snapshot carries a zone (Asia/Kolkata);
   every order/ticket timestamp is offset-naive. We assume Asia/Kolkata. Flagged.
5. **`premium_support` vs `plan` mismatch.** ACCT-004 is `Enterprise` but
   `premium_support=False`, while ACCT-001 (also Enterprise) is True. It is
   undefined what `premium_support` gates (24x7? add-on?). The v3 policy states
   Enterprise P1 as "30 minutes, 24x7" at the *plan* level with no premium gate.
   Ambiguity flagged — do not silently tie coverage to this flag.
6. **Historical resolutions are wrong, not merely stale** (both closed tickets).
   Confirmed against the governing sources — see conflict register. This is by
   design and is the central trap.
7. **No orphaned FKs / impossible dates found.** All `account_id` values in
   orders/tickets resolve to real accounts; all dates fall on/before the
   snapshot except forward-looking pickup *windows* (e.g. ORD-1001 window ends
   11:30, 30 min after snapshot), which is legitimate for still-open orders.
8. **Numeric fields stored as text** in the workbook cells (extracted with
   `dtype=object`); ingestion into SQLite must cast `shipment_fee_inr` to int
   and the booleans to real booleans.
