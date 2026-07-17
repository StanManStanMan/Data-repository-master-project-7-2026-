# ============================================================
#  Nematode Community Composition — Functional Groups
#  Alluvial plots ordered by urban score
#  Faceted by location A and D
#  Functional groups after Yeates et al. (1993)
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
#  4. Functional group lookup — Yeates et al. (1993)
# ============================================================

functional_groups <- data.frame(
  tax_family = c(
    "Alaimidae", "Cephalobidae", "Monhysteridae",
    "Plectidae", "Rhabditidae", "Microlaimidae", "Odontolaimidae",
    "Diphtherophoridae",
    "Trichodoridae", "Tylenchidae", "Tylenchulidae", "Merliniidae",
    "Dorylaimidae",
    "Nygolaimidae", "Aporcelaimidae",
    "Heterorhabditidae"
  ),
  functional_group = c(
    rep("Bacterivore",  7),
    "Fungivore",
    rep("Plant feeder", 4),
    "Omnivore",
    rep("Predator",     2),
    "Insect parasite"
  ),
  stringsAsFactors = FALSE
)

# ============================================================
#  5. Pastel colours per functional group
# ============================================================

fg_colours <- c(
  "Bacterivore"     = "#a8c8e8",
  "Fungivore"       = "#f7c59f",
  "Plant feeder"    = "#a8dbd4",
  "Omnivore"        = "#f9e4a0",
  "Predator"        = "#f4a9a8",
  "Insect parasite" = "#c8b4d8"
)

# ============================================================
#  6. Assign functional groups — drop NA and unmatched families
# ============================================================

nem_fg <- nem %>%
  filter(!is.na(tax_family)) %>%
  semi_join(functional_groups, by = "tax_family") %>%
  left_join(functional_groups, by = "tax_family")

# ============================================================
#  7. Prepare alluvial data
# ============================================================

fg_data <- nem_fg %>%
  group_by(location, sample, functional_group) %>%
  summarise(hits = n(), .groups = "drop") %>%
  group_by(location, sample) %>%
  mutate(rel_hits = hits / sum(hits)) %>%
  ungroup() %>%
  left_join(urban_lookup, by = c("sample", "location")) %>%
  arrange(location, urban_score) %>%
  mutate(
    sample_label     = paste0("S", sample, "\n(", round(urban_score, 2), ")"),
    functional_group = factor(
      functional_group,
      levels = c("Bacterivore", "Fungivore", "Plant feeder",
                 "Omnivore", "Predator", "Insect parasite")
    )
  ) %>%
  group_by(location) %>%
  mutate(sample_label = factor(sample_label, levels = unique(sample_label))) %>%
  ungroup()

# ============================================================
#  8. Plot
# ============================================================

p_fg <- ggplot(fg_data,
               aes(x        = sample_label,
                   y        = rel_hits,
                   alluvium = functional_group,
                   stratum  = functional_group,
                   fill     = functional_group,
                   label    = functional_group)) +
  geom_alluvium(alpha = 0.6) +
  geom_stratum(alpha = 0.8, width = 0.4, colour = "white", linewidth = 0.3) +
  geom_text(stat = "stratum", size = 3.5, check_overlap = TRUE, colour = "grey20") +
  facet_wrap(~ location, scales = "free_x",
             labeller = labeller(location = c(A = "Amsterdam", D = "Dronten"))) +
  scale_fill_manual(values = fg_colours, name = "Functional group") +
  scale_y_continuous(labels = scales::percent) +
  labs(
    title    = "Nematode functional group composition along urban score gradient",
    subtitle = "Functional groups after Yeates et al. (1993)",
    x        = "Sample site (ordered low → high urban score)",
    y        = "Relative abundance"
  ) +
  theme_classic(base_size = 12) +
  theme(
    legend.position = "bottom",
    legend.text     = element_text(size = 10),
    legend.key.size = unit(0.5, "cm"),
    axis.text.x     = element_text(size = 9),
    axis.text.y     = element_text(size = 10),
    axis.title      = element_text(size = 11),
    strip.text      = element_text(size = 11, face = "bold"),
    plot.title      = element_text(size = 13, face = "bold"),
    plot.subtitle   = element_text(size = 10)
  )

print(p_fg)
