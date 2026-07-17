# ============================================================
#  Nematode composition — BLASTN
#  Barplots: all families and all species (total supporting reads)
# ============================================================

library(readxl)
library(dplyr)
library(ggplot2)

# ============================================================
#  1. Load data
# ============================================================

blastn_raw <- read_excel("C:/Users/stanv/Desktop/master_project/data/Rstudio analysis/ncbiblast_split.xlsx")

blastn_raw <- blastn_raw %>%
  rename(
    urban_score = `urban score`,
    total_reads = `total supporting reads`
  ) %>%
  mutate(
    sample   = as.integer(sample),
    week     = as.integer(week),
    location = as.character(location)
  )

# Filter Nematoda and remove sample/week == 0
nem <- blastn_raw %>%
  filter(grepl("nematod", tax_phylum, ignore.case = TRUE)) %>%
  filter(sample != 0, week != 0)

# ============================================================
#  2. Family-level barplot
#     Total supporting reads per family, ordered ascending
# ============================================================

family_counts <- nem %>%
  filter(!is.na(tax_family)) %>%
  group_by(tax_family) %>%
  summarise(
    total_reads = sum(total_reads, na.rm = TRUE),
    .groups     = "drop"
  ) %>%
  arrange(total_reads) %>%
  mutate(tax_family = factor(tax_family, levels = tax_family))

total_families <- nrow(family_counts)

p_families <- ggplot(family_counts,
                     aes(x = tax_family, y = total_reads)) +
  geom_bar(stat = "identity", fill = "lightgreen") +
  coord_flip() +
  labs(
    title = paste0("Nematode families (n = ", total_families, ")"),
    x     = "Family",
    y     = "Total supporting reads"
  ) +
  theme_classic() +
  theme(
    axis.text.y = element_text(size = 8)
  )

print(p_families)

# ============================================================
#  3. Species-level barplot
#     Total supporting reads per species, ordered ascending
# ============================================================

species_counts <- nem %>%
  filter(!is.na(tax_species)) %>%
  group_by(tax_species) %>%
  summarise(
    total_reads = sum(total_reads, na.rm = TRUE),
    .groups     = "drop"
  ) %>%
  arrange(total_reads) %>%
  mutate(tax_species = factor(tax_species, levels = tax_species))

total_species <- nrow(species_counts)

p_species <- ggplot(species_counts,
                    aes(x = tax_species, y = total_reads)) +
  geom_bar(stat = "identity", fill = "lightblue") +
  coord_flip() +
  labs(
    title = paste0("Nematode species (n = ", total_species, ")"),
    x     = "Species",
    y     = "Total supporting reads"
  ) +
  theme_classic() +
  theme(
    axis.text.y = element_text(size = 8)
  )

print(p_species)
