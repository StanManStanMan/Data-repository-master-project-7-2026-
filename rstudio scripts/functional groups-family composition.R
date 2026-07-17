# ============================================================
#  Nematode families — BLASTN
#  Alluvial plot: Functional group → Family
#  Side by side: Location A | Location D
#  Functional groups: Yeates et al. (1993) — Table 1 + family listings
# ============================================================

library(readxl)
library(dplyr)
library(ggplot2)
library(ggalluvial)
library(patchwork)

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

nem <- blastn_raw %>%
  filter(grepl("nematod", tax_phylum, ignore.case = TRUE)) %>%
  filter(sample != 0, week != 0)

# ============================================================
#  2. Functional group lookup — Yeates et al. (1993)
# ============================================================

functional_groups <- data.frame(
  tax_family = c(
    "Alaimidae", "Cephalobidae", "Monhysteridae",
    "Plectidae", "Rhabditidae",
    "Microlaimidae",
    "Odontolaimidae",
    "Diphtherophoridae",
    "Trichodoridae", "Tylenchidae", "Tylenchulidae", "Merliniidae",
    "Dorylaimidae",
    "Nygolaimidae", "Aporcelaimidae",
    "Heterorhabditidae"
  ),
  functional_group = c(
    rep("Bacterivore",   7),
    "Fungivore",
    rep("Plant feeder",  4),
    "Omnivore",
    rep("Predator",      2),
    "Insect parasite"
  ),
  stringsAsFactors = FALSE
)

# ============================================================
#  3. Pastel colour palettes
# ============================================================

fg_colours <- c(
  "Bacterivore"      = "#a8c8e8",
  "Fungivore"        = "#f7c59f",
  "Plant feeder"     = "#a8dbd4",
  "Omnivore"         = "#f9e4a0",
  "Predator"         = "#f4a9a8",
  "Insect parasite"  = "#c8b4d8"
)

family_colours <- c(
  "Alaimidae"          = "#b8d4ec",
  "Cephalobidae"       = "#9ec4e4",
  "Monhysteridae"      = "#c8dff0",
  "Plectidae"          = "#85b4d8",
  "Rhabditidae"        = "#6aa4cc",
  "Microlaimidae"      = "#d8eaf5",
  "Odontolaimidae"     = "#4e94bc",
  "Diphtherophoridae"  = "#f7c59f",
  "Trichodoridae"      = "#7ecec5",
  "Tylenchidae"        = "#a8dbd4",
  "Tylenchulidae"      = "#c2e8e3",
  "Merliniidae"        = "#5bbdb3",
  "Dorylaimidae"       = "#f9e4a0",
  "Nygolaimidae"       = "#f4a9a8",
  "Aporcelaimidae"     = "#f9c8c7",
  "Heterorhabditidae"  = "#c8b4d8"
)

# ============================================================
#  4. Build presence/absence data per location
# ============================================================

family_pa <- nem %>%
  filter(!is.na(tax_family)) %>%
  distinct(location, tax_family) %>%
  left_join(functional_groups, by = "tax_family") %>%
  mutate(
    functional_group = ifelse(is.na(functional_group), "Unclassified", functional_group),
    weight = 1
  )

# Sanity check
unmatched <- family_pa %>% filter(functional_group == "Unclassified")
if (nrow(unmatched) > 0) {
  cat("WARNING: unmatched families (check spelling):\n")
  print(unmatched$tax_family)
} else {
  cat("All families matched.\n")
}

cat("\nFunctional group assignments:\n")
print(family_pa %>% distinct(tax_family, functional_group) %>% arrange(functional_group, tax_family))

# ============================================================
#  5. Helper function — one alluvial plot per location
# ============================================================

make_alluvial <- function(data, loc) {
  
  d <- data %>% filter(location == loc)
  
  ggplot(d,
         aes(axis1 = functional_group,
             axis2 = tax_family,
             y     = weight)) +
    scale_x_discrete(
      limits = c("Functional group", "Family"),
      expand = c(0.15, 0.05)
    ) +
    geom_alluvium(aes(fill = functional_group),
                  width    = 0.3,
                  alpha    = 0.85,
                  knot.pos = 0.4) +
    geom_stratum(aes(fill = after_stat(stratum)),
                 width     = 0.3,
                 colour    = "white",
                 linewidth = 0.4) +
    scale_fill_manual(
      values = c(fg_colours, family_colours),
      guide  = "none"
    ) +
    geom_text(stat   = "stratum",
              aes(label = after_stat(stratum)),
              size   = 3.5,
              colour = "black") +
    labs(
      title = paste0("Location ", loc),
      x     = "",
      y     = "Presence (equal-weight flows)"
    ) +
    theme_classic() +
    theme(
      axis.text.y  = element_blank(),
      axis.ticks.y = element_blank()
    )
}

p_A <- make_alluvial(family_pa, "A")
p_D <- make_alluvial(family_pa, "D")

# ============================================================
#  6. Custom legend
# ============================================================

legend_data <- family_pa %>%
  distinct(tax_family, functional_group) %>%
  arrange(functional_group, tax_family)

fg_order <- c("Bacterivore", "Fungivore", "Plant feeder",
              "Omnivore", "Predator", "Insect parasite")

legend_rows <- do.call(rbind, lapply(fg_order, function(fg) {
  fams <- legend_data %>% filter(functional_group == fg)
  if (nrow(fams) == 0) return(NULL)
  header <- data.frame(
    label     = fg,
    colour    = fg_colours[fg],
    is_header = TRUE,
    stringsAsFactors = FALSE
  )
  entries <- data.frame(
    label     = paste0("  ", fams$tax_family),
    colour    = family_colours[fams$tax_family],
    is_header = FALSE,
    stringsAsFactors = FALSE
  )
  rbind(header, entries)
}))

legend_rows$y <- nrow(legend_rows):1

p_legend <- ggplot(legend_rows, aes(x = 0, y = y)) +
  geom_tile(aes(fill = colour),
            width     = 0.4,
            height    = 0.8,
            colour    = "white",
            linewidth = 0.3) +
  geom_text(aes(label    = label,
                fontface = ifelse(is_header, "bold", "plain")),
            x      = 0.3,
            hjust  = 0,
            size   = 3.5,
            colour = "grey20") +
  scale_fill_identity() +
  scale_x_continuous(limits = c(-0.3, 4)) +
  theme_void() +
  theme(plot.margin = margin(5, 5, 5, 5))

# ============================================================
#  7. Combine: A | D | legend
# ============================================================

p_combined <- p_A + p_D + p_legend +
  plot_layout(widths = c(2, 2, 1)) +
  plot_annotation(
    title    = "Nematode family composition by location",
    subtitle = "Functional groups after Yeates et al. (1993)",
    theme    = theme(
      plot.title    = element_text(size = 13, face = "bold"),
      plot.subtitle = element_text(size = 9)
    )
  )

print(p_combined)
