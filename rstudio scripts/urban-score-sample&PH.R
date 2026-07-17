# ============================================================
#  Quick plots:
#  1. Urban score per sample (A vs D)
#  2. Urban score over pH (A vs D) — all weeks, trendline +
#     Spearman correlation coefficients per location
# ============================================================

library(readxl)
library(dplyr)
library(ggplot2)
library(patchwork)

# ============================================================
#  1. Load data
# ============================================================

blastn_raw <- read_excel("C:/Users/stanv/Desktop/master_project/data/Rstudio analysis/ncbiblast_split.xlsx")

blastn_raw <- blastn_raw %>%
  rename(urban_score = `urban score`) %>%
  mutate(location = as.character(location),
         sample   = as.integer(sample))

# One row per sample × location
site_data <- blastn_raw %>%
  filter(sample != 0) %>%
  distinct(sample, location, urban_score) %>%
  mutate(location_label = ifelse(location == "A", "Amsterdam", "Dronten"))

# ============================================================
#  2. pH table
# ============================================================

ph_table <- data.frame(
  sample   = as.integer(c(1,2,3,4,5,6, 1,2,3,4,5,6, 1,2,3,4,5,6,
                          1,2,3,4,5,6, 1,2,3,4,5,6, 1,2,3,4,5,6)),
  location = c(rep("D",6), rep("A",6),
               rep("D",6), rep("A",6),
               rep("D",6), rep("A",6)),
  week     = as.integer(c(rep(1,12), rep(2,12), rep(3,12))),
  pH       = c(
    8.23, 7.51, 8.13, 6.81, 8.20, 8.18,
    7.58, 7.03, 7.61, 7.47, 7.53, 6.66,
    8.40, 7.87, 7.85, 7.29, 7.92, 8.28,
    8.02, 7.76, 8.22, 7.83, 7.69, 7.57,
    8.29, 8.05, 8.24, 7.46, 8.25, 8.38,
    7.99, 7.70, 8.25, 7.98, 7.83, 7.52
  ),
  stringsAsFactors = FALSE
) %>%
  mutate(location_label = ifelse(location == "A", "Amsterdam", "Dronten")) %>%
  left_join(site_data %>% select(sample, location, urban_score),
            by = c("sample", "location"))

# Colour palette
loc_colours <- c("Amsterdam" = "#f4a9a8", "Dronten" = "#a8c8e8")

# ============================================================
#  3. Spearman correlations per location
# ============================================================

spearman_labels <- ph_table %>%
  group_by(location_label) %>%
  summarise(
    rho = cor(pH, urban_score, method = "spearman"),
    p   = cor.test(pH, urban_score, method = "spearman")$p.value,
    .groups = "drop"
  ) %>%
  mutate(
    label = paste0(location_label, ": ρ = ", round(rho, 2),
                   ", p = ", round(p, 3))
  )

# Position labels in top-left of plot
label_x <- min(ph_table$pH, na.rm = TRUE)
label_y <- c(max(ph_table$urban_score, na.rm = TRUE),
             max(ph_table$urban_score, na.rm = TRUE) - 0.05)

spearman_labels$x <- label_x
spearman_labels$y <- label_y

# ============================================================
#  4. Plot 1: Urban score per sample
# ============================================================

p1 <- ggplot(site_data,
             aes(x = sample, y = urban_score,
                 colour = location_label, group = location_label)) +
  geom_line(linewidth = 0.8) +
  geom_point(size = 3) +
  scale_colour_manual(values = loc_colours, name = "Location") +
  scale_x_continuous(breaks = 1:6) +
  labs(
    title = "Urban score per sample site",
    x     = "Sample",
    y     = "Urban score"
  ) +
  theme_classic() +
  theme(legend.position = "bottom")

# ============================================================
#  5. Plot 2: Urban score over pH + Spearman labels
# ============================================================

p2 <- ggplot(ph_table,
             aes(x = pH, y = urban_score,
                 colour = location_label)) +
  geom_point(size = 3, alpha = 1) +
  geom_smooth(aes(group = location_label),
              method    = "lm",
              se        = FALSE,
              linewidth = 0.8,
              linetype  = "dashed") +
  geom_text(data = spearman_labels,
            aes(x = x, y = y, label = label, colour = location_label),
            hjust       = 0,
            size        = 3,
            show.legend = FALSE) +
  scale_colour_manual(values = loc_colours, name = "Location") +
  labs(
    title = "Urban score over pH",
    x     = "pH",
    y     = "Urban score"
  ) +
  theme_classic() +
  theme(legend.position = "bottom")

# ============================================================
#  6. Combine side by side
# ============================================================

p_combined <- p1 + p2 +
  plot_layout(guides = "collect") &
  theme(legend.position = "bottom")

print(p_combined)
