# Data-repository-master-project-7-2026-
Data repository master project 7/2026 Nematode community composition and diversity Across a small-scale urbanisation gradient

Folder Descriptions & contents
appendixes&protocols
Lab notes and protocols used during the project.
CTAB protocol.pdf — CTAB DNA extraction protocol
lab notes.pdf — lab notes from sample processing
nanopore_protocol.docx — protocol for processing Nanopore sequencing data

easy-combo&blast
NCBI BLAST pipeline for sequence matching against online databases.
FASTAS-HERE/ — input FASTA sequences to be blasted
RESULTS/ — BLAST output results
full-processing.py — script that runs the full BLAST pipeline
README_BLAST.txt — instructions for running the BLAST pipeline

excel files
Compiled data tables and results in Excel format.
final-data.xlsx — final measured data for each sample
locationchar.xlsx — location characteristics per sample site, used in Rstudio
ncbiblast_split.xlsx — NCBI BLAST results split by sample, used in Rstudio
nembaseblast_split.xlsx — NemaBase BLAST results split by sample

full-nanopore pipeline
Nanopore sequencing classification pipeline.
fastq_pass/ — raw FASTQ files from Nanopore sequencing
fastq_pass.zip — archived version of raw FASTQ files
nanopore_pipeline.py — full classification pipeline script
README.txt — instructions for running the Nanopore pipeline

nemabase
Local VSEARCH-based pipeline for matching sequences against the NemaBase 18S database.
18SNemaBase-main/ — NemaBase reference database
match-nemabase.py — script to run NemaBase database matching
nemabase.xlsx — data to be matched in NemaBase
nemabase_results.xlsx — results of NemaBase matching
query_sequences.fasta — query sequences used as input
vsearch.exe — VSEARCH for Windows
vsearch_hits.txt — raw VSEARCH output
README.txt — instructions for running the NemaBase pipeline

qgis
Spatial data and QGIS project files for mapping and urban score analysis.
GHS_BUILT_C_MSZ_E2018_*.tif — Global Human Settlement built-up surface raster (2018)
GHS_POP_E2025_*.tif — Global Human Settlement population raster (2025)
WVL_2021_005m_*.tif — green area coverage raster (2021)
imperviousnesstotal.tif — total impervious surface raster
Labelled places.json — GeoJSON with labelled sampling locations
maps.qgz — main QGIS project file
qgis.zip — archived version of QGIS project
scripts/ — QGIS processing scripts

rstudio scripts
R scripts for statistical analysis of nematode community data.
species-composition.R — species and family composition analysis across all samples
species-diversity-analysis.R — species level richness analysis
family-species-composition.R — family and species composition per city
family diversity analysis.R — family level richness analysis
functional-group-composition.R — family functional group composition
functional groups-family composition.R — functional groups per family
urban-scores.R — urban score calculation and graphs
urban-score-sample&PH.R — urban score and pH graphs

Notes
Raw data (FASTQ, FASTA) should not be edited manually.
Scripts can be rerun to regenerate results from raw inputs.
See individual README.txt files inside easy-combo&blast/ and full-nanopore pipeline/ for pipeline-specific instructions.
