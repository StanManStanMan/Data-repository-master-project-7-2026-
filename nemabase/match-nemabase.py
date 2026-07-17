"""
match_against_nemabase.py
--------------------------
Matches nematode sequences from nemabase.xlsx against the
18S_NemaBase.fasta database using VSEARCH (local alignment).
Taxonomy is parsed directly from the VSEARCH target ID (full FASTA header).

Requirements:
    pip install pandas openpyxl
    sudo apt install vsearch   (in WSL)

Folder structure expected:
    nemabase.xlsx
    match_against_nemabase.py
    18SNemaBase-main/
        18S_NemaBase_fix.fasta/
            18S_NemaBase.fasta

Usage:
    python match_against_nemabase.py

Output:
    nemabase_results.xlsx   -- original Excel with NemaBase taxonomy columns added
    query_sequences.fasta   -- temporary FASTA of query sequences
    vsearch_hits.txt        -- raw VSEARCH output (tab-separated)
"""

import os
import re
import subprocess
import pandas as pd

# ── CONFIGURATION ──────────────────────────────────────────────────────────────
EXCEL_FILE     = "nemabase.xlsx"
NEMABASE_FASTA = os.path.join("18SNemaBase-main", "18S_NemaBase_fix.fasta", "18S_NemaBase.fasta")
VSEARCH_EXE    = "vsearch"
QUERY_FASTA    = "query_sequences.fasta"
VSEARCH_OUT    = "vsearch_hits.txt"
OUTPUT_EXCEL   = "nemabase_results.xlsx"

IDENTITY_THRESHOLD = 0.95   # 97% is standard for nematode species-level identification
THREADS = 16
# ───────────────────────────────────────────────────────────────────────────────


def check_vsearch():
    try:
        result = subprocess.run([VSEARCH_EXE, "--version"],
                                capture_output=True, text=True)
        print(f"[OK] VSEARCH found: {result.stderr.splitlines()[0]}")
    except FileNotFoundError:
        raise EnvironmentError("vsearch not found. Install with: sudo apt install vsearch")


def excel_to_fasta(excel_path, fasta_path):
    df = pd.read_excel(excel_path)
    if "sequence" not in df.columns:
        raise ValueError("Column 'sequence' not found in Excel file.")
    written = 0
    with open(fasta_path, "w") as f:
        for idx, row in df.iterrows():
            seq = "".join(str(row["sequence"]).strip().upper().split())
            if seq and seq != "NAN":
                f.write(f">seq_{idx}\n{seq}\n")
                written += 1
    print(f"[OK] Wrote {written} query sequences to {fasta_path}")
    return df


def run_vsearch(query_fasta, db_fasta, output_file, identity, threads):
    cmd = [
        VSEARCH_EXE,
        "--usearch_global", query_fasta,
        "--db", db_fasta,
        "--id", str(identity),
        "--blast6out", output_file,
        "--threads", str(threads),
        "--top_hits_only",
        "--maxaccepts", "1",
        "--maxrejects", "256",
        "--query_cov", "0.5",
        "--strand", "both",
    ]
    print(f"[..] Running VSEARCH (identity >= {identity*100:.0f}%, both strands)...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("VSEARCH stderr:\n", result.stderr)
        raise RuntimeError("VSEARCH failed.")
    for line in result.stderr.splitlines():
        if any(k in line for k in ["Matching", "matched", "Total"]):
            print(f"  {line.strip()}")
    print(f"[OK] VSEARCH finished. Results in {output_file}")


def parse_target_id(target_id):
    """
    Parse taxonomy directly from the VSEARCH target ID, which is the full
    FASTA header, e.g.:
        KX789710.1.1693_Eukaryota;Animalia;Nematoda;NA_subphylum;...;Genus;Species

    Split on the first '_Eukaryota' to get accession and taxonomy string.
    """
    match = re.match(r'^(.+?)_(Eukaryota;.+)$', target_id.strip())
    if match:
        accession    = match.group(1)
        taxonomy_str = match.group(2).strip()
    else:
        accession    = target_id.strip()
        taxonomy_str = ""

    tax_levels = taxonomy_str.split(";")

    def get(lst, i):
        val = lst[i].strip() if i < len(lst) else ""
        if val.upper().startswith("NA_") or val == "NA" or val.lower().startswith("unknown"):
            return ""
        return val

    return {
        "nb_hit_accession": accession,
        "nb_taxonomy_str":  taxonomy_str,
        "nb_superkingdom":  get(tax_levels, 0),
        "nb_kingdom":       get(tax_levels, 1),
        "nb_phylum":        get(tax_levels, 2),
        "nb_subphylum":     get(tax_levels, 3),
        "nb_superclass":    get(tax_levels, 4),
        "nb_class":         get(tax_levels, 5),
        "nb_subclass":      get(tax_levels, 6),
        "nb_superorder":    get(tax_levels, 7),
        "nb_order":         get(tax_levels, 8),
        "nb_suborder":      get(tax_levels, 9),
        "nb_infraorder":    get(tax_levels, 10),
        "nb_superfamily":   get(tax_levels, 11),
        "nb_family":        get(tax_levels, 12),
        "nb_subfamily":     get(tax_levels, 13),
        "nb_genus":         get(tax_levels, 14),
        "nb_species":       get(tax_levels, 15).replace("_", " ") if len(tax_levels) > 15 else "",
    }


def parse_vsearch_output(vsearch_file):
    """Parse VSEARCH blast6 output, extracting taxonomy from the target ID."""
    hits = {}
    with open(vsearch_file, "r") as f:
        for line in f:
            cols = line.strip().split("\t")
            if len(cols) < 2:
                continue
            query_id  = cols[0]
            target_id = cols[1]
            pct_id    = float(cols[2]) if len(cols) > 2 else 0.0

            tax = parse_target_id(target_id)
            tax["nb_pct_identity"] = pct_id
            hits[query_id] = tax

    print(f"[OK] Parsed {len(hits)} VSEARCH hits.")
    return hits


def merge_results(df, hits):
    new_cols = [
        "nb_hit_accession", "nb_pct_identity", "nb_taxonomy_str",
        "nb_superkingdom", "nb_kingdom", "nb_phylum", "nb_subphylum",
        "nb_superclass", "nb_class", "nb_subclass", "nb_superorder",
        "nb_order", "nb_suborder", "nb_infraorder", "nb_superfamily",
        "nb_family", "nb_subfamily", "nb_genus", "nb_species",
    ]
    for col in new_cols:
        df[col] = None

    for idx, row in df.iterrows():
        seq_id = f"seq_{idx}"
        if seq_id in hits:
            for col in new_cols:
                df.at[idx, col] = hits[seq_id].get(col, None)

    matched = df["nb_hit_accession"].notna().sum()
    print(f"[OK] {matched}/{len(df)} sequences matched to NemaBase.")
    return df


def main():
    print("=" * 55)
    print("  NemaBase Sequence Matcher")
    print("=" * 55)

    check_vsearch()
    df = excel_to_fasta(EXCEL_FILE, QUERY_FASTA)
    run_vsearch(QUERY_FASTA, NEMABASE_FASTA, VSEARCH_OUT,
                IDENTITY_THRESHOLD, THREADS)
    hits = parse_vsearch_output(VSEARCH_OUT)
    df = merge_results(df, hits)

    df.to_excel(OUTPUT_EXCEL, index=False)
    print(f"[OK] Results saved to {OUTPUT_EXCEL}")
    print("=" * 55)
    print("Done!")


if __name__ == "__main__":
    main()
