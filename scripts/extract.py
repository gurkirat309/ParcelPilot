"""Extract the ParcelPilot source corpus into data/extracted/.

- Verifies exactly 7 correctly-named raw files before doing anything.
- Every PDF -> data/extracted/<name>.txt with `--- PAGE n ---` boundary markers.
- Every XLSX sheet -> data/extracted/<sheet>.csv plus a printed profile
  (columns, dtypes, null counts, low-cardinality uniques, 5 sample rows).

Run from the project root:  python scripts/extract.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pdfplumber

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "extracted"

EXPECTED = {
    "01_Support_Policy_v3_CURRENT.pdf",
    "02_Support_Policy_v2_DEPRECATED.pdf",
    "03_Cancellation_and_Service_Credit_SOP_v4.pdf",
    "04_Product_Operations_Guide_and_Known_Issues.pdf",
    "05_Northstar_Logistics_Enterprise_Agreement.pdf",
    "06_LumenWorks_Service_Agreement.pdf",
    "ParcelPilot_Assessment_Data.xlsx",
}

# Treat a column as low-cardinality (worth listing every unique value) if it
# has at most this many distinct non-null values.
LOW_CARD_MAX = 25


def verify_raw() -> list[Path]:
    """Assert exactly the 7 expected files are present. STOP otherwise."""
    if not RAW.is_dir():
        sys.exit(f"STOP: raw directory not found: {RAW}")

    found = {p.name for p in RAW.iterdir() if p.is_file()}
    print(f"Found {len(found)} file(s) in {RAW}:")
    for name in sorted(found):
        print(f"  - {name}")

    missing = EXPECTED - found
    extra = found - EXPECTED
    if missing or extra:
        print()
        if missing:
            print("STOP: missing or misnamed (expected but not found):")
            for name in sorted(missing):
                print(f"  ! {name}")
        if extra:
            print("STOP: unexpected file(s) present:")
            for name in sorted(extra):
                print(f"  ? {name}")
        sys.exit(1)

    print("\nOK: exactly 7 expected files present.\n")
    return [RAW / name for name in sorted(EXPECTED)]


def extract_pdf(path: Path) -> None:
    out_path = OUT / (path.stem + ".txt")
    parts: list[str] = []
    with pdfplumber.open(path) as pdf:
        n_pages = len(pdf.pages)
        for i, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            parts.append(f"--- PAGE {i} ---\n{text}")
    out_path.write_text("\n\n".join(parts) + "\n", encoding="utf-8")
    print(f"  PDF  {path.name}: {n_pages} page(s) -> {out_path.name}")


def profile_sheet(name: str, df: pd.DataFrame) -> None:
    print(f"\n{'=' * 70}\nSHEET: {name}   ({len(df)} rows x {len(df.columns)} cols)\n{'=' * 70}")

    print("\nColumns / dtypes / null counts:")
    for col in df.columns:
        nulls = int(df[col].isna().sum())
        nunique = int(df[col].nunique(dropna=True))
        print(f"  {col!r}: dtype={df[col].dtype}  nulls={nulls}  unique={nunique}")

    print(f"\nLow-cardinality column values (<= {LOW_CARD_MAX} uniques):")
    any_low = False
    for col in df.columns:
        uniques = df[col].dropna().unique()
        if 0 < len(uniques) <= LOW_CARD_MAX:
            any_low = True
            vals = sorted(map(repr, uniques))
            print(f"  {col!r} ({len(uniques)}): {', '.join(vals)}")
    if not any_low:
        print("  (none)")

    print("\nFirst 5 rows:")
    with pd.option_context("display.max_columns", None, "display.width", 200):
        print(df.head(5).to_string())


def extract_xlsx(path: Path) -> None:
    xls = pd.ExcelFile(path, engine="openpyxl")
    print(f"\n  XLSX {path.name}: sheets = {xls.sheet_names}")
    for sheet in xls.sheet_names:
        df = xls.parse(sheet, dtype=object)  # dtype=object to see raw values
        safe = sheet.strip().replace(" ", "_").replace("/", "_")
        csv_path = OUT / f"{safe}.csv"
        df.to_csv(csv_path, index=False, encoding="utf-8")
        print(f"    sheet {sheet!r} -> {csv_path.name}")
        profile_sheet(sheet, df)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    files = verify_raw()

    print("Extracting PDFs...")
    for path in files:
        if path.suffix.lower() == ".pdf":
            extract_pdf(path)

    print("\nExtracting workbook...")
    for path in files:
        if path.suffix.lower() == ".xlsx":
            extract_xlsx(path)

    print("\nDone. Extracted artifacts in", OUT)


if __name__ == "__main__":
    main()
