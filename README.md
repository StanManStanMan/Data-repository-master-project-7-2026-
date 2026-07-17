# Data-repository-master-project-7-2026-
Data repository master project 7/2026 Nematode community composition and diversity Across a small-scale urbanisation gradient

Folder Descriptions & contents
### appendixes&protocols

Lab notes and protocols used during the project.

`CTAB protocol.pdf` — CTAB DNA extraction protocol<br><br>
`lab notes.pdf` — lab notes from sample processing<br><br>
`nanopore_protocol.docx` — protocol for processing Nanopore sequencing data

---

### easy-combo&blast

NCBI BLAST pipeline for sequence matching against online databases.

`FASTAS-HERE/` — input FASTA sequences to be blasted<br><br>
`RESULTS/` — BLAST output results<br><br>
`full-processing.py` — script that runs the full BLAST pipeline<br><br>
`README_BLAST.txt` — instructions for running the BLAST pipeline

---

### excel files

Compiled data tables and results in Excel format.

`final-data.xlsx` — final measured data for each sample<br><br>
`locationchar.xlsx` — location characteristics per sample site, used in Rstudio<br><br>
`ncbiblast_split.xlsx` — NCBI BLAST results split by sample, used in Rstudio<br><br>
`nembaseblast_split.xlsx` — NemaBase BLAST results split by sample

---

### full-nanopore pipeline

Nanopore sequencing classification pipeline.

`fastq_pass/` — raw FASTQ files from Nanopore sequencing<br><br>
`fastq_pass.zip` — archived version of raw FASTQ files<br><br>
`nanopore_pipeline.py` — full classification pipeline script<br><br>
`README.txt` — instructions for running the Nanopore pipeline

---

### nemabase

Local VSEARCH-based pipeline for matching sequences against the NemaBase 18S database.

`18SNemaBase-main/` — NemaBase reference database<br><br>
`match-nemabase.py` — script to run NemaBase database matching<br><br>
`nemabase.xlsx` — data to be matched in NemaBase<br><br>
`nemabase_results.xlsx` — results of NemaBase matching<br><br>
`query_sequences.fasta` — query sequences used as input<br><br>
`vsearch.exe` — VSEARCH for Windows<br><br>
`vsearch_hits.txt` — raw VSEARCH output<br><br>
`README.txt` — instructions for running the NemaBase pipeline

---

### qgis

Spatial data and QGIS project files for mapping and urban score analysis.

`GHS_BUILT_C_MSZ_E2018_*.tif` — Global Human Settlement built-up surface raster (2018)<br><br>
`GHS_POP_E2025_*.tif` — Global Human Settlement population raster (2025)<br><br>
`WVL_2021_005m_*.tif` — green area coverage raster (2021)<br><br>
`imperviousnesstotal.tif` — total impervious surface raster<br><br>
`Labelled places.json` — GeoJSON with labelled sampling locations<br><br>
`maps.qgz` — main QGIS project file<br><br>
`qgis.zip` — archived version of QGIS project<br><br>
`scripts/` — QGIS processing scripts

---

### rstudio scripts

R scripts for statistical analysis of nematode community data.

`species-composition.R` — species and family composition analysis across all samples<br><br>
`species-diversity-analysis.R` — species level richness analysis<br><br>
`family-species-composition.R` — family and species composition per city<br><br>
`family diversity analysis.R` — family level richness analysis<br><br>
`functional-group-composition.R` — family functional group composition<br><br>
`functional groups-family composition.R` — functional groups per family<br><br>
`urban-scores.R` — urban score calculation and graphs<br><br>
`urban-score-sample&PH.R` — urban score and pH graphs

---
