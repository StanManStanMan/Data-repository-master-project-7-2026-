# ============================================================
#  Nematode Community Composition Visualisation
#  Alluvial plots ordered by urban score
#  Faceted by location A and D
#  Family and species level — pastel colour palette
# ============================================================

library(ggplot2)
library(ggalluvial)
library(dplyr)
library(readxl)

# ============================================================
#  1. Load data
# ============================================================

raw <- read_excel("C:/Users/stanv/Desktop/master_project/data/Rstudio analysis/ncbiblast_split.xlsx")

raw <- raw %>%
  rename(urban_score = `urban score`) %>%
  mutate(
    sample      = as.integer(sample),
    week        = as.integer(week),
    location    = as.character(location),
    urban_score = as.numeric(urban_score)
  )

# ============================================================
#  2. Filter Nematoda
# ============================================================

nem <- raw %>%
  filter(grepl("nematod", tax_phylum, ignore.case = TRUE)) %>%
  filter(sample != 0, week != 0)

# ============================================================
#  3. Urban score lookup per sample x location
# ============================================================

urban_lookup <- nem %>%
  select(sample, location, urban_score) %>%
  distinct()

# ============================================================
#  4. Pastel palette generator
# ============================================================

pastel_palette <- function(taxa) {
  base_pastels <- c(
    "#a8c8e8", "#f4a9a8", "#a8dbd4", "#f7c59f",
    "#c8b4d8", "#f9e4a0", "#b4d8b4", "#f4c2d8",
    "#b4c8f4", "#e8d4a8", "#d4e8a8", "#f4d4b4",
    "#a8b4d8", "#e8a8c8", "#c8e8a8", "#d8c8f4"
  )
  taxa_no_other <- taxa[taxa != "Other"]
  n <- length(taxa_no_other)
  if (n <= length(base_pastels)) {
    cols <- base_pastels[seq_len(n)]
  } else {
    cols <- colorRampPalette(base_pastels)(n)
  }
  named <- setNames(cols, taxa_no_other)
  if ("Other" %in% taxa) named["Other"] <- "#d9d9d9"
  named
}

# ============================================================
#  Helper function
# ============================================================

prepare_alluvial <- function(data, tax_col, min_rel_abundance = 0.01) {
  
  counts <- data %>%
    filter(!is.na(.data[[tax_col]])) %>%
    group_by(location, sample, taxon = .data[[tax_col]]) %>%
    summarise(hits = n(), .groups = "drop") %>%
    group_by(location, sample) %>%
    mutate(rel_hits = hits / sum(hits)) %>%
    ungroup()
  
  taxa_to_keep <- counts %>%
    group_by(taxon) %>%
    summarise(max_rel = max(rel_hits)) %>%
    filter(max_rel >= min_rel_abundance) %>%
    pull(taxon)
  
  cat("Number of taxa shown:", length(taxa_to_keep), "\n")
  
  counts <- counts %>%
    mutate(taxon = ifelse(taxon %in% taxa_to_keep, taxon, "Other")) %>%
    group_by(location, sample, taxon) %>%
    summarise(hits = sum(hits), .groups = "drop") %>%
    group_by(location, sample) %>%
    mutate(rel_hits = hits / sum(hits)) %>%
    ungroup()
  
  counts <- counts %>%
    left_join(urban_lookup, by = c("sample", "location")) %>%
    arrange(location, urban_score) %>%
    mutate(sample_label = paste0("S", sample, "\n(", round(urban_score, 2), ")")) %>%
    group_by(location) %>%
    mutate(sample_label = factor(sample_label, levels = unique(sample_label))) %>%
    ungroup()
  
  return(counts)
}

# ============================================================
#  Family level
# ============================================================

fam_data    <- prepare_alluvial(nem, "tax_family", min_rel_abundance = 0.01)
fam_colours <- pastel_palette(unique(fam_data$taxon))

p_fam <- ggplot(fam_data,
                aes(x        = sample_label,
                    y        = rel_hits,
                    alluvium = taxon,
                    stratum  = taxon,
                    fill     = taxon,
                    label    = taxon)) +
  geom_alluvium(alpha = 0.6) +
  geom_stratum(alpha = 0.8, width = 0.4, colour = "white", linewidth = 0.3) +
  geom_text(stat = "stratum", size = 3.5, check_overlap = TRUE, colour = "grey20") +
  facet_wrap(~ location, scales = "free_x",
             labeller = labeller(location = c(A = "Amsterdam", D = "Dronten"))) +
  scale_fill_manual(values = fam_colours, name = "Family") +
  scale_y_continuous(labels = scales::percent) +
  labs(title = "Nematode family composition along urban score gradient",
       x     = "Sample site (ordered low → high urban score)",
       y     = "Relative abundance") +
  theme_classic(base_size = 12) +
  theme(
    legend.position = "bottom",
    legend.text     = element_text(size = 10),
    legend.key.size = unit(0.4, "cm"),
    axis.text.x     = element_text(size = 9),
    axis.text.y     = element_text(size = 10),
    axis.title      = element_text(size = 11),
    strip.text      = element_text(size = 11, face = "bold"),
    plot.title      = element_text(size = 13, face = "bold")
  )

print(p_fam)

# ============================================================
#  Species level
# ============================================================

spe_data    <- prepare_alluvial(nem, "tax_species", min_rel_abundance = 0.01)
spe_colours <- pastel_palette(unique(spe_data$taxon))

p_spe <- ggplot(spe_data,
                aes(x        = sample_label,
                    y        = rel_hits,
                    alluvium = taxon,
                    stratum  = taxon,
                    fill     = taxon,
                    label    = taxon)) +
  geom_alluvium(alpha = 0.6) +
  geom_stratum(alpha = 0.8, width = 0.4, colour = "white", linewidth = 0.3) +
  geom_text(stat = "stratum", size = 3.5, check_overlap = TRUE, colour = "grey20") +
  facet_wrap(~ location, scales = "free_x",
             labeller = labeller(location = c(A = "Amsterdam", D = "Dronten"))) +
  scale_fill_manual(values = spe_colours, name = "Species") +
  scale_y_continuous(labels = scales::percent) +
  labs(title = "Nematode species composition along urban score gradient",
       x     = "Sample site (ordered low → high urban score)",
       y     = "Relative abundance") +
  theme_classic(base_size = 12) +
  theme(
    legend.position = "bottom",
    legend.text     = element_text(size = 10),
    legend.key.size = unit(0.4, "cm"),
    axis.text.x     = element_text(size = 9),
    axis.text.y     = element_text(size = 10),
    axis.title      = element_text(size = 11),
    strip.text      = element_text(size = 11, face = "bold"),
    plot.title      = element_text(size = 13, face = "bold")
  )

print(p_spe)
