# full-processing.py

import pandas as pd
import numpy as np
import os
import glob
import re
import time
import threading
import sys
import signal
import requests
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import concurrent.futures
from Bio.Blast import NCBIWWW, NCBIXML

# ── CONFIG ────────────────────────────────────────────────────────────────────
EMAIL       = "your@email.com"   # ← replace with your email (NCBI requirement)
MIN_PERCENT = 2.0                # minimum % of total reads to keep

# BLAST parameters
BLAST_PROGRAM    = "blastn"
BLAST_DATABASE   = "nt"
BLAST_HITLIST    = 1
BLAST_MEGABLAST  = True
BLAST_WORD_SIZE  = 28
BLAST_EXPECT     = 0.001
BLAST_FILTER     = "T"
BLAST_TIMEOUT    = 120           # ← seconds before a hung qblast is abandoned
# ─────────────────────────────────────────────────────────────────────────────

BASE_DIR        = Path(__file__).parent
FASTA_DIR       = BASE_DIR / "FASTAS-HERE"
RESULTS_DIR     = BASE_DIR / "RESULTS"

DIR_PREPARED    = RESULTS_DIR / "0_prepared"
DIR_EXCEL       = RESULTS_DIR / "1_excel"
DIR_FILTERED    = RESULTS_DIR / "2_filtered"
DIR_COMBINED    = RESULTS_DIR / "3_combined"
DIR_BLASTED     = RESULTS_DIR / "4_blasted"

COMBINED_FILE   = DIR_COMBINED / "combined.xlsx"
BLASTED_FILE    = DIR_BLASTED  / "blasted.xlsx"

READS_COLUMN    = "total supporting reads"
SEQ_COLUMN      = "sequence"

RANKS = ["kingdom", "phylum", "class", "order", "family", "genus", "species"]
BLAST_COLS = [
    "blast_accession", "blast_hit_id", "blast_description", "blast_species",
    "blast_common_name", "blast_score", "blast_evalue", "blast_identity_%",
    "tax_kingdom", "tax_phylum", "tax_class", "tax_order",
    "tax_family", "tax_genus", "tax_species",
]

HEADERS = {"User-Agent": f"BlastScript/1.0 (contact: {EMAIL})"}

for d in [FASTA_DIR, DIR_PREPARED, DIR_EXCEL, DIR_FILTERED, DIR_COMBINED, DIR_BLASTED]:
    d.mkdir(parents=True, exist_ok=True)

# ══════════════════════════════════════════════════════════════════════════════
# STEP 0 — PREPARE FASTA FILES (replicate Word find/replace)
# ══════════════════════════════════════════════════════════════════════════════
def prepare_fasta(filepath, out_dir):
    text = filepath.read_text(encoding="utf-8", errors="ignore")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("_", "\t")
    PLACEHOLDER = "%"
    text = text.replace("\n>", PLACEHOLDER)
    text = text.replace("\n", "\t")
    text = text.replace(PLACEHOLDER, "\n>")
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    out_path = out_dir / filepath.name
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out_path, len(lines)

def step0_prepare_fastas():
    print("\n" + "═"*60)
    print("STEP 0 — Preparing FASTA files (Word-style find/replace)")
    print("═"*60)

    fasta_files = [
        f for f in list(FASTA_DIR.glob("*.fasta")) + list(FASTA_DIR.glob("*.fa"))
        if not f.name.startswith("~$")
    ]

    if not fasta_files:
        print(f"  ✗ No .fasta / .fa files found in {FASTA_DIR}. Aborting.")
        sys.exit(1)

    print(f"  Found {len(fasta_files)} file(s). Saving prepared copies → {DIR_PREPARED}\n")

    for fasta_file in fasta_files:
        out_path, n_records = prepare_fasta(fasta_file, DIR_PREPARED)
        print(f"  ✓ {fasta_file.name}  →  {out_path.name}  ({n_records} records)")

    print("\n  Step 0 complete.\n")

# ══════════════════════════════════════════════════════════════════════════════
# STEP 1 — FASTA → EXCEL  (reads from 0_prepared)
# ══════════════════════════════════════════════════════════════════════════════
def parse_fasta(filepath):
    sample = int(filepath.stem[-2:])
    records = []
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line.startswith(">"):
                continue
            parts = line[1:].split("\t")
            if len(parts) < 9:
                print(f"  ⚠ Skipping malformed line ({len(parts)} fields): {line[:60]}...")
                continue
            records.append({
                "sample":                 sample,
                "total supporting reads": int(parts[7]),
                "sequence":               parts[8],
            })
    return records

def step1_fasta_to_excel():
    print("\n" + "═"*60)
    print("STEP 1 — Converting prepared FASTA files to Excel")
    print("═"*60)

    fasta_files = [
        f for f in list(DIR_PREPARED.glob("*.fasta")) + list(DIR_PREPARED.glob("*.fa"))
        if not f.name.startswith("~$")
    ]

    if not fasta_files:
        print(f"  ✗ No prepared files found in {DIR_PREPARED}. Aborting.")
        sys.exit(1)

    for fasta_file in fasta_files:
        print(f"  Processing: {fasta_file.name}")
        records = parse_fasta(fasta_file)
        if not records:
            print(f"  ⚠ No records found, skipping.")
            continue
        df = pd.DataFrame(records, columns=["sample", "total supporting reads", "sequence"])
        out_file = DIR_EXCEL / (fasta_file.stem + ".xlsx")
        df.to_excel(out_file, index=False)
        print(f"  ✓ {len(records)} records → {out_file.name}")

    print("  Step 1 complete.\n")

# ══════════════════════════════════════════════════════════════════════════════
# STEP 2 — REMOVE SEQUENCES BELOW 2% & COMBINE
# ══════════════════════════════════════════════════════════════════════════════
def step2_filter_and_combine():
    print("═"*60)
    print("STEP 2 — Filtering (<2%) and combining Excel files")
    print("═"*60)

    excel_files = glob.glob(str(DIR_EXCEL / "*.xlsx"))
    if not excel_files:
        print("  ✗ No Excel files found in 1_excel/. Aborting.")
        sys.exit(1)

    print(f"  Found {len(excel_files)} file(s).\n")
    all_filtered = []

    for filepath in excel_files:
        filename = os.path.basename(filepath)
        df = pd.read_excel(filepath)

        if READS_COLUMN not in df.columns:
            print(f"  ⚠ Skipping {filename}: column '{READS_COLUMN}' not found.")
            continue

        total_reads = df[READS_COLUMN].sum()
        min_reads   = (MIN_PERCENT / 100) * total_reads
        before      = len(df)
        df_filtered = df[df[READS_COLUMN] >= min_reads].copy()
        after       = len(df_filtered)

        df_filtered.insert(0, "source_file", filename)

        out_file = DIR_FILTERED / filename
        df_filtered.to_excel(out_file, index=False)

        all_filtered.append(df_filtered)

        print(f"  {filename}")
        print(f"    Total reads : {total_reads}")
        print(f"    Threshold   : {min_reads:.1f} ({MIN_PERCENT}% of {total_reads})")
        print(f"    Kept        : {after}/{before}  |  Removed: {before - after}")
        print()

    if not all_filtered:
        print("  ✗ No data to combine. Aborting.")
        sys.exit(1)

    final_df = pd.concat(all_filtered, ignore_index=True)
    final_df.to_excel(COMBINED_FILE, index=False, engine="openpyxl")
    print(f"  ✓ Combined {len(all_filtered)} file(s) → {COMBINED_FILE.name}")
    print(f"  Total rows: {len(final_df)}")
    print("  Step 2 complete.\n")

# ══════════════════════════════════════════════════════════════════════════════
# STEP 3 — BLAST + TAXONOMY
# ══════════════════════════════════════════════════════════════════════════════
VALID_BASES = set("ACGTNacgtn")

def is_valid_sequence(s):
    s = str(s).strip()
    if not s or s.lower() == "nan":
        return False
    if len(s) < 10:
        return False
    return (sum(1 for c in s if c in VALID_BASES) / len(s)) >= 0.9

def extract_species(description):
    match = re.search(r'\[([A-Z][a-z]+ [a-z]+.*?)\]', description)
    if match:
        return match.group(1).strip()
    words = description.split()
    if len(words) >= 2 and words[0][0].isupper() and words[1][0].islower():
        return f"{words[0]} {words[1]}"
    return None

# ── Taxonomy helpers ──────────────────────────────────────────────────────────

def get_taxid_via_elink(accession):
    """Most reliable: NCBI elink nucleotide → taxonomy."""
    try:
        r = requests.get(
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/elink.fcgi",
            params={
                "dbfrom":  "nucleotide",
                "db":      "taxonomy",
                "id":      accession,
                "retmode": "json",
                "email":   EMAIL,
            },
            headers=HEADERS,
            timeout=15,
        )
        links = r.json()["linksets"][0]["linksetdbs"][0]["links"]
        return str(links[0]) if links else None
    except Exception:
        return None

def get_taxid_from_accession(accession):
    """Fallback: parse taxon tag from GenBank XML."""
    try:
        r = requests.get(
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi",
            params={"db": "nucleotide", "id": accession, "rettype": "gb", "retmode": "xml", "email": EMAIL},
            headers=HEADERS, timeout=15
        )
        m = re.search(r'<GBQualifier_value>taxon:(\d+)</GBQualifier_value>', r.text)
        return m.group(1) if m else None
    except Exception:
        return None

def get_taxid_from_species(species_name):
    """Search NCBI taxonomy by species name string."""
    try:
        r = requests.get(
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
            params={"db": "taxonomy", "term": species_name, "retmode": "json", "email": EMAIL},
            headers=HEADERS, timeout=10
        )
        ids = r.json().get("esearchresult", {}).get("idlist", [])
        return ids[0] if ids else None
    except Exception:
        return None

def resolve_taxid(accession, species):
    """Try all methods in order, return first taxid found."""
    # 1. elink (most reliable)
    taxid = get_taxid_via_elink(accession) if accession else None

    # 2. exact species name
    if taxid is None and species:
        taxid = get_taxid_from_species(species)

    # 3. cleaned genus + species only (strips strain/subsp. noise)
    if taxid is None and species:
        clean = " ".join(species.split()[:2])
        if clean != species:
            taxid = get_taxid_from_species(clean)

    # 4. GenBank XML fallback
    if taxid is None and accession:
        taxid = get_taxid_from_accession(accession)

    return taxid

def get_lineage_from_taxid(taxid):
    lineage = {rank: None for rank in RANKS}
    try:
        r = requests.get(
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi",
            params={"db": "taxonomy", "id": taxid, "retmode": "xml", "email": EMAIL},
            headers=HEADERS, timeout=15
        )
        entries = re.findall(
            r'<Taxon>.*?<TaxId>(\d+)</TaxId>.*?<ScientificName>(.*?)</ScientificName>.*?<Rank>(.*?)</Rank>.*?</Taxon>',
            r.text, re.DOTALL
        )
        for _, name, rank in entries:
            rank = rank.strip().lower()
            if rank in lineage:
                lineage[rank] = name.strip()
        if lineage["species"] is None:
            sp = re.search(r'<ScientificName>(.*?)</ScientificName>', r.text)
            rk = re.search(r'<Rank>(.*?)</Rank>', r.text)
            if sp and rk and rk.group(1).strip().lower() == "species":
                lineage["species"] = sp.group(1).strip()
    except Exception:
        pass
    return lineage

def get_common_name_ncbi(taxid=None, species_name=None):
    try:
        if taxid is None and species_name:
            taxid = get_taxid_from_species(species_name)
        if taxid is None:
            return None
        r = requests.get(
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi",
            params={"db": "taxonomy", "id": taxid, "retmode": "json", "email": EMAIL},
            headers=HEADERS, timeout=10
        )
        record = r.json().get("result", {}).get(str(taxid), {})
        common = record.get("commonname", "").strip()
        return common if common else None
    except Exception:
        return None

def get_common_name_wikipedia(species_name):
    try:
        r = requests.get(
            "https://en.wikipedia.org/api/rest_v1/page/summary/" + species_name.replace(" ", "_"),
            headers=HEADERS, timeout=10
        )
        if r.status_code != 200:
            return None
        data = r.json()
        title   = data.get("title", "")
        extract = data.get("extract", "")
        desc    = data.get("description", "")
        if title.lower() != species_name.lower():
            return title
        m = re.search(
            r'(?:commonly (?:known|called) as|also known as|called the?)\s+([a-z][a-z\s\-]+)',
            extract, re.IGNORECASE
        )
        if m:
            return m.group(1).strip().rstrip(",.")
        return desc if desc else None
    except Exception:
        return None

def get_common_name(taxid=None, species_name=None):
    name = get_common_name_ncbi(taxid=taxid, species_name=species_name)
    return name if name else (get_common_name_wikipedia(species_name) if species_name else None)

# ── Graceful interrupt ────────────────────────────────────────────────────────
interrupted = False

def handle_interrupt(sig, frame):
    global interrupted
    interrupted = True
    print("\n\n  ⚠ Interrupted! Saving results collected so far...")

signal.signal(signal.SIGINT, handle_interrupt)

# ── Spinner ───────────────────────────────────────────────────────────────────
stop_spinner = False
print_lock   = threading.Lock()

def spinner_func():
    chars = ["|", "/", "-", "\\"]
    idx = 0
    start = time.time()
    while not stop_spinner:
        elapsed = int(time.time() - start)
        m, s = divmod(elapsed, 60)
        sys.stdout.write(f"\r  {chars[idx % 4]} Waiting for NCBI... {m:02d}:{s:02d}  (Ctrl+C to stop & save)")
        sys.stdout.flush()
        idx += 1
        time.sleep(0.2)
    sys.stdout.write("\r" + " " * 60 + "\r")
    sys.stdout.flush()

# ── Single-row BLAST worker ───────────────────────────────────────────────────
def _run_qblast(seq):
    """Runs qblast in isolation so it can be wrapped with a timeout."""
    return NCBIWWW.qblast(
        program=BLAST_PROGRAM,
        database=BLAST_DATABASE,
        sequence=seq,
        hitlist_size=BLAST_HITLIST,
        megablast=BLAST_MEGABLAST,
        word_size=BLAST_WORD_SIZE,
        filter=BLAST_FILTER,
        expect=BLAST_EXPECT,
    )

def blast_one(i, row, total):
    seq = str(row[SEQ_COLUMN]).strip()

    if not is_valid_sequence(seq):
        with print_lock:
            print(f"  [{i+1}/{total}] Skipping invalid sequence: {seq[:60]}")
        return i, None

    with print_lock:
        print(f"  [{i+1}/{total}] BLASTing: {seq[:40]}...")

    try:
        # ── Run qblast with a hard timeout ───────────────────────────────────
        with ThreadPoolExecutor(max_workers=1) as blast_ex:
            future = blast_ex.submit(_run_qblast, seq)
            try:
                result_handle = future.result(timeout=BLAST_TIMEOUT)
            except concurrent.futures.TimeoutError:
                with print_lock:
                    print(f"  [{i+1}/{total}] ✗ BLAST timed out after {BLAST_TIMEOUT}s, skipping.")
                return i, None
        # ─────────────────────────────────────────────────────────────────────

        blast_record = NCBIXML.read(result_handle)

        if blast_record.alignments:
            aln  = blast_record.alignments[0]
            hsp  = aln.hsps[0]

            accession    = str(aln.accession)
            hit_id       = str(aln.hit_id)
            description  = str(aln.hit_def)
            score        = float(hsp.score)
            evalue       = float(hsp.expect)
            identity_pct = round((hsp.identities / hsp.align_length) * 100, 2)
            species      = extract_species(description)

            with print_lock:
                print(f"    [{i+1}/{total}] Looking up taxonomy for: {species}")

            # ── Improved taxonomy resolution ──────────────────────────────────
            taxid       = resolve_taxid(accession, species)
            lineage     = get_lineage_from_taxid(taxid) if taxid else {r: None for r in RANKS}
            common_name = get_common_name(taxid=taxid, species_name=species)
            # ─────────────────────────────────────────────────────────────────

            with print_lock:
                print(f"    [{i+1}/{total}] ✓ {description[:80]}")
                print(f"      Species: {species} | Common: {common_name}")
                print(f"      Accession: {accession} | Score: {score} | E-value: {evalue} | Identity: {identity_pct}%")
                print(f"      Lineage: {lineage['kingdom']} → {lineage['phylum']} → {lineage['class']} → {lineage['order']} → {lineage['family']} → {lineage['genus']} → {lineage['species']}")

            return i, {
                "blast_accession":   accession,
                "blast_hit_id":      hit_id,
                "blast_description": description,
                "blast_species":     species,
                "blast_common_name": common_name,
                "blast_score":       score,
                "blast_evalue":      evalue,
                "blast_identity_%":  identity_pct,
                **{f"tax_{rank}": lineage[rank] for rank in RANKS},
            }
        else:
            with print_lock:
                print(f"    [{i+1}/{total}] ✗ No hits found.")
            return i, None

    except Exception as e:
        if not interrupted:
            with print_lock:
                print(f"    ✗ BLAST error on row {i+1}: {e}")
        return i, None

# ── Step 3 ────────────────────────────────────────────────────────────────────
def step3_blast():
    global stop_spinner, interrupted

    print("═"*60)
    print("STEP 3 — BLASTing sequences (3 concurrent queries)")
    print("═"*60)
    print(f"  Settings: program={BLAST_PROGRAM} | db={BLAST_DATABASE} | megablast={BLAST_MEGABLAST}")
    print(f"            word_size={BLAST_WORD_SIZE} | expect={BLAST_EXPECT} | filter={BLAST_FILTER} | hits={BLAST_HITLIST}")
    print(f"            timeout={BLAST_TIMEOUT}s per query\n")

    # ── Resume logic: load existing blasted.xlsx if present ──────────────────
    if BLASTED_FILE.exists():
        df = pd.read_excel(BLASTED_FILE)
        # Ensure all blast columns exist (in case file is from an older run)
        for col in BLAST_COLS:
            if col not in df.columns:
                df[col] = None
        # A row is considered done if it has a blast_accession OR was already
        # attempted and returned no hits (blast_description is not null but
        # blast_accession may be). We use blast_description as the done marker.
        done_mask  = df["blast_description"].notna()
        done_count = done_mask.sum()
        print(f"  ↻ Resuming from existing blasted.xlsx")
        print(f"    Already done : {done_count}/{len(df)} rows — skipping these.\n")
    else:
        df = pd.read_excel(COMBINED_FILE)
        for col in BLAST_COLS:
            df[col] = None
        done_mask  = pd.Series([False] * len(df))
        print(f"  Starting fresh — {len(df)} rows to process.\n")
    # ─────────────────────────────────────────────────────────────────────────

    # Only queue rows that are not yet done
    rows  = [(i, row) for i, row in df.iterrows() if not done_mask[i]]
    total = len(df)

    if not rows:
        print("  ✓ All rows already processed. Nothing to do.")
        return

    print(f"  Rows remaining : {len(rows)}/{total}\n")

    stop_spinner = False
    spinner_thread = threading.Thread(target=spinner_func)
    spinner_thread.start()

    batch_size = 3

    try:
        for batch_start in range(0, len(rows), batch_size):
            if interrupted:
                break

            batch = rows[batch_start : batch_start + batch_size]

            with ThreadPoolExecutor(max_workers=batch_size) as executor:
                futures = {
                    executor.submit(blast_one, i, row, total): i
                    for i, row in batch
                }
                for future in as_completed(futures):
                    if interrupted:
                        break
                    idx, result = future.result()
                    if result:
                        for key, val in result.items():
                            df.at[idx, key] = val
                    else:
                        # Mark as attempted (no hit) so it won't be retried
                        df.at[idx, "blast_description"] = "NO_HIT"

            # ── Save after every batch so progress is never lost ──────────────
            stop_spinner = True
            spinner_thread.join()
            df.to_excel(BLASTED_FILE, index=False, engine="openpyxl")
            done_now = df["blast_description"].notna().sum()
            print(f"    ✓ Progress saved ({done_now}/{total} rows done)")
            # ─────────────────────────────────────────────────────────────────

            if batch_start + batch_size < len(rows) and not interrupted:
                print("    Waiting 3 seconds...")
                time.sleep(3)

            stop_spinner = False
            spinner_thread = threading.Thread(target=spinner_func)
            spinner_thread.start()

    finally:
        stop_spinner = True
        spinner_thread.join()
        df.to_excel(BLASTED_FILE, index=False, engine="openpyxl")

    if interrupted:
        print(f"\n  Partial results saved → {BLASTED_FILE}")
    else:
        print(f"\n  ✓ All done! Results saved → {BLASTED_FILE}")
        print("  Step 3 complete.\n")

# ══════════════════════════════════════════════════════════════════════════════
# RUN PIPELINE
# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("\n" + "█"*60)
    print("  FASTA → BLAST PIPELINE")
    print("█"*60)
    print(f"  Input  : {FASTA_DIR}")
    print(f"  Output : {RESULTS_DIR}")

    step0_prepare_fastas()
    step1_fasta_to_excel()
    step2_filter_and_combine()
    step3_blast()

    print("\n" + "█"*60)
    print("  PIPELINE COMPLETE")
    print("█"*60)
