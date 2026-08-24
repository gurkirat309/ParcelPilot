"""Generate SYNTHETIC tickets for the Problem 1 ops board.

ANALYTICS ONLY. These are clearly-labelled synthetic rows (is_synthetic=1 at
ingest) that amplify signals already present in the real corpus so proactive
detection has something real to find:
  - a KI-208 bulk-upload surge across MULTIPLE accounts near the snapshot,
  - a KI-211 SwiftShip "still BOOKED" cluster,
  - a second HTTP-500 outage account (multi-customer signal with TKT-501),
  - plus low-volume baseline rows on earlier days so a spike is visible.

They are NEVER an authority source and never reach the customer/agent repository.
Timestamps are fixed strings (no wall clock — Rule 3). Reproducible.
"""

from __future__ import annotations

import csv
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "data" / "synthetic"
COLS = ["ticket_id", "account_id", "created_at", "status", "subject",
        "description", "channel", "assigned_to", "last_customer_message_at",
        "historical_resolution"]

# subject/description crafted so the signals classifier maps them to known issues.
ROWS = [
    # --- baseline (pre-spike), low volume on 08-10-11 ---
    ("TKT-901", "ACCT-004", "2026-08-10 15:20", "closed", "Bulk upload failed once",
     "A 3,300-row CSV failed to upload yesterday; retried and it worked.", "email", "Maya",
     "2026-08-10 16:00", ""),
    ("TKT-902", "ACCT-001", "2026-08-11 12:05", "closed", "SwiftShip status lag",
     "Order briefly showed BOOKED after the driver had picked it up.", "chat", "Rohit",
     "2026-08-11 12:30", ""),

    # --- KI-208 bulk-upload SURGE across multiple accounts on snapshot day ---
    ("TKT-910", "ACCT-004", "2026-08-16 09:50", "open", "Bulk upload fails for 3,600-row CSV",
     "Large CSV upload fails around 70%. Single shipment creation still works.", "chat", "Maya",
     "2026-08-16 10:05", ""),
    ("TKT-911", "ACCT-001", "2026-08-16 10:12", "open", "Bulk upload keeps failing",
     "Uploading a 4,000-row CSV fails repeatedly this morning.", "email", "Rohit",
     "2026-08-16 10:20", ""),
    ("TKT-912", "ACCT-002", "2026-08-16 10:38", "open", "Another large CSV upload failure",
     "Second failed bulk upload today, ~3,800 rows, stalls partway.", "chat", "Maya",
     "2026-08-16 10:44", ""),
    ("TKT-913", "ACCT-004", "2026-08-16 10:55", "open", "CSV import failing again",
     "Bulk import of 3,500 rows fails; smaller files seem fine.", "email", "Rohit",
     "2026-08-16 10:58", ""),

    # --- KI-211 SwiftShip "still BOOKED" cluster ---
    ("TKT-920", "ACCT-002", "2026-08-16 10:30", "open", "SwiftShip order still shows BOOKED",
     "Driver picked up ~15 min ago but the order still shows BOOKED.", "chat", "Maya",
     "2026-08-16 10:40", ""),
    ("TKT-921", "ACCT-004", "2026-08-16 10:22", "open", "Pickup done but status not updated",
     "SwiftShip collected the parcel; ParcelPilot still says BOOKED.", "email", "Rohit",
     "2026-08-16 10:33", ""),

    # --- second outage account (multi-customer HTTP 500 signal with TKT-501) ---
    ("TKT-930", "ACCT-004", "2026-08-16 10:41", "open", "All shipment creation failing",
     "Every user here gets HTTP 500 creating shipments. Viewing works.", "email", "Rohit",
     "2026-08-16 10:50", ""),

    # --- noise / unrelated, so clustering must discriminate ---
    ("TKT-940", "ACCT-003", "2026-08-16 09:35", "open", "Update billing contact email",
     "Please change the billing-contact email on our account.", "email", "Maya",
     "2026-08-16 09:40", ""),
]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "tickets_synthetic.csv"
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(COLS)
        w.writerows(ROWS)
    print(f"Wrote {len(ROWS)} synthetic tickets -> {path}")


if __name__ == "__main__":
    main()
