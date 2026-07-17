#!/usr/bin/env python3
"""
Nanopore Short Amplicon Pipeline
---------------------------------
Run this script from the folder containing the fastq_pass directory.
It will auto-detect barcodes, run NanoPlot QC, NanoFilt, and NGSpeciesID.

Folder structure created:
  compiled/
    raw/                  <- merged per-barcode fastq.gz
    nanoplot_raw/         <- NanoPlot output per barcode (pre-filter)
    filtered/             <- HQ filtered fastq files
    nanoplot_filtered/    <- NanoPlot output per barcode (post-filter)
    NGSpeciesID/          <- NGSpeciesID output per barcode
    fastas/               <- final consensus FASTA files
"""

import os
import sys
import glob
import subprocess
import shutil

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def run(cmd, description=""):
    """Run a shell command and exit on failure."""
    print(f"\n  >> {description}" if description else f"\n  >> Running: {cmd}")
    print(f"     {cmd}")
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print(f"\n[ERROR] Command failed (exit code {result.returncode}):\n  {cmd}")
        sys.exit(1)

def run_soft(cmd, description=""):
    """Run a shell command but continue on failure. Returns True if successful."""
    print(f"\n  >> {description}" if description else f"\n  >> Running: {cmd}")
    print(f"     {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"\n  [WARNING] Command failed for: {description}")
        print(f"  This is likely caused by too few reads in this barcode.")
        print(f"  Error details: {result.stderr.strip().splitlines()[-1] if result.stderr.strip() else 'unknown'}")
        return False
    return True

def make_dir(path):
    os.makedirs(path, exist_ok=True)

def pause(message):
    input(f"\n{'='*60}\n{message}\nPress ENTER to continue...\n{'='*60}\n")

def count_reads_fastq(filepath):
    """Count reads in a .fastq file (lines / 4)."""
    try:
        result = subprocess.run(f"wc -l < {filepath}", shell=True,
                                capture_output=True, text=True)
        lines = int(result.stdout.strip())
        return lines // 4
    except Exception:
        return 0

# ─────────────────────────────────────────────
# STEP 0: DETECT WORKING DIRECTORY & BARCODES
# ─────────────────────────────────────────────

script_dir    = os.getcwd()
fastq_pass_dir = os.path.join(script_dir, "fastq_pass")

if not os.path.isdir(fastq_pass_dir):
    print(f"[ERROR] No 'fastq_pass' folder found in:\n  {script_dir}")
    sys.exit(1)

barcode_dirs = sorted(glob.glob(os.path.join(fastq_pass_dir, "barcode*")))
barcodes     = [os.path.basename(b) for b in barcode_dirs if os.path.isdir(b)]

if not barcodes:
    print("[ERROR] No barcode folders found inside fastq_pass/")
    sys.exit(1)

sample_fastq = glob.glob(os.path.join(barcode_dirs[0], "*.fastq.gz"))
if not sample_fastq:
    print(f"[ERROR] No .fastq.gz files found in {barcode_dirs[0]}")
    sys.exit(1)

flowcell_id = os.path.basename(sample_fastq[0]).split("_")[0]

print("\n" + "="*60)
print("  Nanopore Short Amplicon Pipeline")
print("="*60)
print(f"  Working directory : {script_dir}")
print(f"  fastq_pass folder : {fastq_pass_dir}")
print(f"  Flow cell ID      : {flowcell_id}")
print(f"  Barcodes detected : {', '.join(barcodes)}")
print("="*60)

confirm = input("\nDo these settings look correct? (yes/no): ").strip().lower()
if confirm != "yes":
    print("Aborted. Please check your folder structure and re-run.")
    sys.exit(0)

# ─────────────────────────────────────────────
# STEP 1: SET UP FOLDER STRUCTURE
# ─────────────────────────────────────────────

compiled          = os.path.join(fastq_pass_dir, "compiled")
raw_dir           = os.path.join(compiled, "raw")
nanoplot_raw_dir  = os.path.join(compiled, "nanoplot_raw")
filtered_dir      = os.path.join(compiled, "filtered")
nanoplot_filt_dir = os.path.join(compiled, "nanoplot_filtered")
ngsid_dir         = os.path.join(compiled, "NGSpeciesID")
fastas_dir        = os.path.join(compiled, "fastas")

for d in [raw_dir, nanoplot_raw_dir, filtered_dir, nanoplot_filt_dir, ngsid_dir, fastas_dir]:
    make_dir(d)

print("\n[OK] Folder structure created under compiled/")

# ─────────────────────────────────────────────
# STEP 2: MERGE FASTQ FILES PER BARCODE
# ─────────────────────────────────────────────

print("\n" + "="*60)
print("  STEP 1: Merging FASTQ files per barcode")
print("="*60)

for bc in barcodes:
    bc_path  = os.path.join(fastq_pass_dir, bc)
    out_file = os.path.join(raw_dir, f"{bc}.fastq.gz")
    if os.path.exists(out_file):
        print(f"  [SKIP] {bc}.fastq.gz already exists")
        continue
    cmd = f"cat {bc_path}/{flowcell_id}*.fastq.gz > {out_file}"
    run(cmd, f"Merging {bc}")

print("\n[OK] All barcodes merged.")

# ─────────────────────────────────────────────
# STEP 3: NANOPLOT - RAW QC
# ─────────────────────────────────────────────

print("\n" + "="*60)
print("  STEP 2: NanoPlot QC on raw reads")
print("="*60)

nanoplot_failed = []

for bc in barcodes:
    in_file  = os.path.join(raw_dir, f"{bc}.fastq.gz")
    out_path = os.path.join(nanoplot_raw_dir, bc)
    make_dir(out_path)
    if os.path.exists(os.path.join(out_path, "NanoPlot-report.html")):
        print(f"  [SKIP] NanoPlot already done for {bc}")
        continue
    cmd = (f"NanoPlot -t 12 --fastq_rich {in_file} "
           f"--N50 --verbose --raw -o {out_path}")
    success = run_soft(cmd, f"NanoPlot raw QC: {bc}")
    if not success:
        nanoplot_failed.append(bc)

print("\n[OK] NanoPlot complete.")

if nanoplot_failed:
    print(f"\n  [WARNING] NanoPlot failed for: {', '.join(nanoplot_failed)}")

print(f"\n  NanoPlot reports saved to:\n  {nanoplot_raw_dir}")

# ─────────────────────────────────────────────
# BREAK: MANUAL QC CHECK + BARCODE REVIEW
# ─────────────────────────────────────────────

print("\n" + "="*60)
print("  MANUAL QC CHECK")
print("="*60)
print(f"\n  NanoPlot reports are in:\n  {nanoplot_raw_dir}")
print("\n  Open the NanoPlot-report.html files and inspect read")
print("  length distributions and quality scores.")

pause("Please review the NanoPlot reports before continuing.")

print("\n" + "="*60)
print("  BARCODE CHECK")
print("="*60)

exclude_barcodes = []
exclude_input = input("  Enter any barcodes to exclude (e.g. barcode52 barcode55), or press ENTER to continue: ").strip()
if exclude_input:
    exclude_barcodes = exclude_input.split()
    barcodes = [bc for bc in barcodes if bc not in exclude_barcodes]
    print(f"\n  Excluded: {', '.join(exclude_barcodes)}")
    print(f"  Continuing with: {', '.join(barcodes)}")
else:
    print("\n  No barcodes excluded. Continuing with all barcodes.")

# ─────────────────────────────────────────────
# STEP 4: ASK FOR FILTER PARAMETERS
# ─────────────────────────────────────────────

print("\n" + "="*60)
print("  STEP 3: NanoFilt parameters")
print("="*60)

while True:
    try:
        min_len_input = int(input("  Enter MINIMUM fragment length you want to keep (bp): "))
        max_len_input = int(input("  Enter MAXIMUM fragment length as seen in NanoPlot (bp): "))
        quality       = int(input("  Enter minimum quality score (e.g. 15): "))
        break
    except ValueError:
        print("  [!] Please enter whole numbers only.\n")

min_len = min_len_input
max_len = max_len_input

print(f"\n  You entered        : min={min_len_input} bp, max={max_len_input} bp, q={quality}")
print(f"  Passed to NanoFilt : --length {min_len} --maxlength {max_len}")

confirm = input("\n  Confirm these parameters? (yes/no): ").strip().lower()
if confirm != "yes":
    print("Aborted. Re-run the script to enter new parameters.")
    sys.exit(0)

# ─────────────────────────────────────────────
# STEP 5: NANOFILT - FILTER READS
# ─────────────────────────────────────────────

print("\n" + "="*60)
print("  STEP 4: Filtering reads with NanoFilt")
print("="*60)

for bc in barcodes:
    in_file   = os.path.join(raw_dir, f"{bc}.fastq.gz")
    out_fastq = os.path.join(filtered_dir, f"HQ{bc}.fastq")

    if os.path.exists(out_fastq):
        reads = count_reads_fastq(out_fastq)
        print(f"  [SKIP] HQ{bc}.fastq already exists ({reads} reads)")
        continue

    cmd = (f"zcat {in_file} | NanoFilt -q {quality} "
           f"--length {min_len} --maxlength {max_len} "
           f"--headcrop 30 --tailcrop 30 > {out_fastq}")
    run(cmd, f"NanoFilt: {bc}")

    reads = count_reads_fastq(out_fastq)
    print(f"  [OK] HQ{bc}.fastq: {reads} reads passed filter")
    if reads == 0:
        print(f"  [WARNING] No reads passed the filter for {bc}!")
        print(f"            Consider lowering quality (-q) or adjusting length thresholds.")

print("\n[OK] All barcodes filtered.")

# ─────────────────────────────────────────────
# STEP 6: NANOPLOT - POST-FILTER QC
# ─────────────────────────────────────────────

print("\n" + "="*60)
print("  STEP 5: NanoPlot QC on filtered reads")
print("="*60)

nanoplot_filt_failed = []

for bc in barcodes:
    in_file  = os.path.join(filtered_dir, f"HQ{bc}.fastq")
    out_path = os.path.join(nanoplot_filt_dir, bc)
    make_dir(out_path)
    if os.path.exists(os.path.join(out_path, "NanoPlot-report.html")):
        print(f"  [SKIP] Post-filter NanoPlot already done for {bc}")
        continue
    cmd = (f"NanoPlot -t 12 --fastq {in_file} "
           f"--N50 --verbose --raw -o {out_path}")
    success = run_soft(cmd, f"NanoPlot filtered QC: {bc}")
    if not success:
        nanoplot_filt_failed.append(bc)

if nanoplot_filt_failed:
    print(f"\n  [WARNING] Post-filter NanoPlot failed for: {', '.join(nanoplot_filt_failed)}")
    print("  These barcodes likely have very few reads passing the quality/length filters.")

    exclude_more = input("\n  Exclude any of these from NGSpeciesID? (enter barcode names separated by space, or ENTER to keep all): ").strip()
    if exclude_more:
        extra_exclude = exclude_more.split()
        barcodes = [bc for bc in barcodes if bc not in extra_exclude]
        print(f"  Additionally excluded: {', '.join(extra_exclude)}")

print(f"\n[OK] Post-filter NanoPlot reports saved to:\n  {nanoplot_filt_dir}")

# ─────────────────────────────────────────────
# STEP 7: NGSPECIESID
# ─────────────────────────────────────────────

print("\n" + "="*60)
print("  STEP 6: Running NGSpeciesID")
print("="*60)

CONDA_ENV = "NGSpeciesID"

print(f"\n  Checking conda environment '{CONDA_ENV}'...")
check = subprocess.run(
    f"conda run -n {CONDA_ENV} NGSpeciesID --help",
    shell=True, capture_output=True, text=True
)
if check.returncode != 0:
    print(f"\n[ERROR] Could not find or run NGSpeciesID in conda environment '{CONDA_ENV}'.")
    print("  Check available environments with: conda env list")
    sys.exit(1)

print(f"[OK] Conda environment '{CONDA_ENV}' found and NGSpeciesID is available.")

ngsid_failed = []

for bc in barcodes:
    fastq_file = os.path.join(filtered_dir, f"HQ{bc}.fastq")
    out_folder = os.path.join(ngsid_dir, f"NGSID_{bc}")

    # Skip if already done
    if os.path.isdir(out_folder) and glob.glob(os.path.join(out_folder, "consensus_reference_*.fasta")):
        print(f"  [SKIP] NGSpeciesID already done for {bc}")
        continue

    # Warn and skip if fastq is empty
    reads = count_reads_fastq(fastq_file)
    if reads == 0:
        print(f"  [SKIP] HQ{bc}.fastq is empty — skipping NGSpeciesID.")
        ngsid_failed.append(bc)
        continue

    make_dir(out_folder)
    cmd = (f"conda run -n {CONDA_ENV} "
           f"NGSpeciesID --t 12 --ont --consensus --racon --racon_iter 3 "
           f"--sample_size 10000 --abundance_ratio 0.001 "
           f"--fastq {fastq_file} --outfolder {out_folder}")
    success = run_soft(cmd, f"NGSpeciesID: {bc}")
    if not success:
        ngsid_failed.append(bc)

if ngsid_failed:
    print(f"\n  [WARNING] NGSpeciesID failed for: {', '.join(ngsid_failed)}")
    print("  These barcodes likely had too few reads after filtering.")

print("\n[OK] NGSpeciesID complete.")

# ─────────────────────────────────────────────
# STEP 8: COLLECT FASTA FILES
# ─────────────────────────────────────────────

print("\n" + "="*60)
print("  STEP 7: Collecting consensus FASTA files")
print("="*60)

no_consensus = []

for bc in barcodes:
    ngsid_out  = os.path.join(ngsid_dir, f"NGSID_{bc}")
    fasta_out  = os.path.join(ngsid_out, f"NGSID_{bc}.fasta")
    final_dest = os.path.join(fastas_dir, f"NGSID_{bc}.fasta")

    refs = sorted(glob.glob(os.path.join(ngsid_out, "consensus_reference_*.fasta")))
    if not refs:
        print(f"  [WARNING] No consensus found for {bc} - skipping.")
        no_consensus.append(bc)
        continue

    with open(fasta_out, "w") as out_f:
        for ref in refs:
            with open(ref) as in_f:
                out_f.write(in_f.read())

    shutil.copy(fasta_out, final_dest)
    print(f"  [OK] {bc}: {len(refs)} consensus(es) -> fastas/NGSID_{bc}.fasta")

# ─────────────────────────────────────────────
# DONE
# ─────────────────────────────────────────────

print("\n" + "="*60)
print("  PIPELINE COMPLETE")
print("="*60)

total     = len(barcodes)
succeeded = total - len(set(no_consensus) | set(ngsid_failed))

print(f"""
  Results:
    Total barcodes processed : {total}
    Successful               : {succeeded}
    NGSpeciesID failed       : {len(ngsid_failed)}  {('-> ' + ', '.join(ngsid_failed)) if ngsid_failed else ''}
    No consensus produced    : {len(no_consensus)}  {('-> ' + ', '.join(no_consensus)) if no_consensus else ''}
    Excluded by user         : {len(exclude_barcodes)}  {('-> ' + ', '.join(exclude_barcodes)) if exclude_barcodes else ''}

  Output summary:
  compiled/
  |-- raw/                 merged raw fastq.gz per barcode
  |-- nanoplot_raw/        NanoPlot QC (pre-filter) per barcode
  |-- filtered/            HQ filtered fastq files
  |-- nanoplot_filtered/   NanoPlot QC (post-filter) per barcode
  |-- NGSpeciesID/         NGSpeciesID output per barcode
  |-- fastas/              Final consensus FASTA files

  Next step: BLAST the FASTA files in fastas/ via NCBI for
  taxonomic assignment.
""")
