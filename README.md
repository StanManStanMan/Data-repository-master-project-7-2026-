# Data-repository-master-project-7-2026-
Data repository master project 7/2026 Nematode community composition and diversity Across a small-scale urbanisation gradient

External downloads
Some files are hosted on goofgle drive due to size.

File	Folder	Download
lab notes.pdf	appendixes&protocols/	https://drive.google.com/file/d/10ObKXovQVlZOvMJA5eHXQABqQSlUhxWj/view?usp=sharing
fastq_pass.zip	full-nanopore pipeline/	https://drive.google.com/file/d/1G_Os0LZkrFkCLTa2yqEI9Q7DYJgKxYbF/view?usp=sharing
qgis.zip	qgis/	https://drive.google.com/file/d/1O5JdlBlMic4nvrMyNJxeLDGu__kFKjfe/view?usp=sharing
After downloading fastq_pass.zip, extract it into the fastq_pass folder.

After downloading qgis.zip, extract it into qgis/ to access all raster layers and the QGIS project file.

Folder Descriptions & contents
appendixes&protocols
Lab notes and protocols used during the project.

CTAB protocol.pdf — CTAB DNA extraction protocol

lab notes.pdf — lab notes from sample processing (download externally, see above)

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

fastq_pass/ — raw FASTQ files from Nanopore sequencing (extract from fastq_pass.zip, download externally, see above)

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

scripts/ — QGIS processing scripts

qgis.zip — full QGIS project including all raster layers and project file (download externally, see above)

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
