# ============================================================
#  Nematode Family Diversity — Analysis
#  Phylum: Nematoda | Response: family richness
#  Main: Spearman correlations + Mann-Whitney
#  Supporting: LMM with all variables (results table)
# ============================================================

library(lme4)
library(lmerTest)
library(ggplot2)
library(dplyr)
library(knitr)
library(readxl)

# ============================================================
#  1. Load data
# ============================================================

raw <- read_excel("C:/Users/stanv/Desktop/master_project/data/Rstudio analysis/ncbiblast_split.xlsx")

raw <- raw %>%
  rename(urban_score = `urban score`) %>%
  mutate(
    sample   = as.integer(sample),
    week     = as.integer(week),
    location = as.character(location)
  )

# ============================================================
#  2. pH lookup table
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
)

# ============================================================
#  3. Filter Nematoda, compute family richness
# ============================================================

nem <- raw %>%
  filter(grepl("nematod", tax_phylum, ignore.case = TRUE))

diversity <- nem %>%
  group_by(sample, location, week) %>%
  summarise(
    family_richness = n_distinct(tax_family, na.rm = TRUE),
    .groups = "drop"
  )

# ============================================================
#  4. Merge urban score and pH
# ============================================================

urban_meta <- raw %>%
  select(sample, location, week, urban_score) %>%
  distinct() %>%
  filter(!is.na(urban_score))

diversity <- diversity %>%
  left_join(urban_meta, by = c("sample", "location", "week")) %>%
  left_join(ph_table,   by = c("sample", "location", "week")) %>%
  filter(sample != 0, week != 0)

cat("Columns:", names(diversity), "\n")
cat("Missing values:\n")
print(colSums(is.na(diversity)))
cat("\nFinal dataset (n =", nrow(diversity), "):\n")
print(diversity, n = Inf)

# ============================================================
#  5. Site-level averages
# ============================================================

site_avg <- diversity %>%
  group_by(sample, location) %>%
  summarise(
    mean_richness = mean(family_richness),
    urban_score   = first(urban_score),
    mean_pH       = mean(pH),
    .groups = "drop"
  )

site_A <- site_avg[site_avg$location == "A", ]
site_D <- site_avg[site_avg$location == "D", ]

cat("\nSite-level averages (n =", nrow(site_avg), "):\n")
print(site_avg)

# ============================================================
#  6. Main analyses
# ============================================================

cat("\n========== Mann-Whitney U: family richness ~ location ==========\n")
mw <- wilcox.test(family_richness ~ location, data = diversity, exact = FALSE)
print(mw)
cat(sprintf("Median family richness — A: %.1f | D: %.1f\n",
            median(diversity$family_richness[diversity$location == "A"]),
            median(diversity$family_richness[diversity$location == "D"])))

cat("\n========== Kruskal-Wallis: family richness ~ week ==========\n")
kw <- kruskal.test(family_richness ~ as.factor(week), data = diversity)
print(kw)

# ============================================================
#  7. Spearman correlations — per location
# ============================================================

cat("\n========== Spearman: family richness ~ urban score | Location A ==========\n")
sp_urban_A <- cor.test(site_A$mean_richness, site_A$urban_score,
                       method = "spearman", exact = FALSE)
print(sp_urban_A)

cat("\n========== Spearman: family richness ~ urban score | Location D ==========\n")
sp_urban_D <- cor.test(site_D$mean_richness, site_D$urban_score,
                       method = "spearman", exact = FALSE)
print(sp_urban_D)

cat("\n========== Spearman: family richness ~ pH | Location A ==========\n")
sp_ph_A <- cor.test(site_A$mean_richness, site_A$mean_pH,
                    method = "spearman", exact = FALSE)
print(sp_ph_A)

cat("\n========== Spearman: family richness ~ pH | Location D ==========\n")
sp_ph_D <- cor.test(site_D$mean_richness, site_D$mean_pH,
                    method = "spearman", exact = FALSE)
print(sp_ph_D)

# ============================================================
#  8. Plots
# ============================================================

y_max_div <- max(diversity$family_richness, na.rm = TRUE)

# p1 — Family richness by location (+ Mann-Whitney annotation)
p1 <- ggplot(diversity, aes(x = location, y = family_richness, fill = location)) +
  geom_boxplot(alpha = 0.6, outlier.shape = NA) +
  geom_jitter(width = 0.1, size = 2) +
  annotate("segment",
           x = 1, xend = 2,
           y = y_max_div * 1.08, yend = y_max_div * 1.08) +
  annotate("segment", x = 1, xend = 1,
           y = y_max_div * 1.06, yend = y_max_div * 1.08) +
  annotate("segment", x = 2, xend = 2,
           y = y_max_div * 1.06, yend = y_max_div * 1.08) +
  annotate("text",
           x = 1.5, y = y_max_div * 1.12,
           label = paste0("Mann-Whitney\np = ", round(mw$p.value, 3)),
           size = 3.2, hjust = 0.5) +
  scale_y_continuous(expand = expansion(mult = c(0.05, 0.18))) +
  labs(title = "Nematode family richness by location",
       x = "Location", y = "Family richness") +
  theme_classic() +
  theme(legend.position = "none")
print(p1)

# p2 — Richness ~ urban score
p2 <- ggplot(site_avg, aes(x = urban_score, y = mean_richness,
                           colour = location, label = sample)) +
  geom_point(size = 4) +
  geom_smooth(aes(colour = location), method = "lm", se = TRUE) +
  geom_text(vjust = -0.8, size = 3) +
  labs(title = "Mean nematode family richness vs Urban score",
       subtitle = paste0(
         "A: rho = ", round(sp_urban_A$estimate, 2), ", p = ", round(sp_urban_A$p.value, 3),
         "   |   D: rho = ", round(sp_urban_D$estimate, 2), ", p = ", round(sp_urban_D$p.value, 3)
       ),
       x = "Urban score", y = "Mean family richness", colour = "Location") +
  theme_classic()
print(p2)

# p3 — Richness ~ pH
p3 <- ggplot(site_avg, aes(x = mean_pH, y = mean_richness,
                           colour = location, label = sample)) +
  geom_point(size = 4) +
  geom_smooth(aes(colour = location), method = "lm", se = TRUE) +
  geom_text(vjust = -0.8, size = 3) +
  labs(title = "Mean nematode family richness vs pH",
       subtitle = paste0(
         "A: rho = ", round(sp_ph_A$estimate, 2), ", p = ", round(sp_ph_A$p.value, 3),
         "   |   D: rho = ", round(sp_ph_D$estimate, 2), ", p = ", round(sp_ph_D$p.value, 3)
       ),
       x = "Mean pH", y = "Mean family richness", colour = "Location") +
  theme_classic()
print(p3)

# p4 — Richness over weeks (+ Kruskal-Wallis annotation)
p4 <- ggplot(diversity, aes(x = as.factor(week), y = family_richness, fill = location)) +
  geom_boxplot(alpha = 0.6) +
  annotate("text",
           x = 2, y = y_max_div * 1.10,
           label = paste0("Kruskal-Wallis\np = ", round(kw$p.value, 3)),
           size = 3.2, hjust = 0.5) +
  scale_y_continuous(expand = expansion(mult = c(0.05, 0.18))) +
  labs(title = "Nematode family richness across weeks",
       x = "Week", y = "Family richness", fill = "Location") +
  theme_classic()
print(p4)

cat("\n========== Boxplot stats: family richness by location ==========\n")
stats_location <- diversity %>%
  group_by(location) %>%
  summarise(
    min    = min(family_richness),
    Q1     = quantile(family_richness, 0.25),
    med    = median(family_richness),
    Q3     = quantile(family_richness, 0.75),
    max    = max(family_richness),
    IQR    = Q3 - Q1,
    .groups = "drop"
  )
print(stats_location)

cat("\n========== Boxplot stats: family richness by week + location ==========\n")
stats_week_location <- diversity %>%
  group_by(week, location) %>%
  summarise(
    min    = min(family_richness),
    Q1     = quantile(family_richness, 0.25),
    med    = median(family_richness),
    Q3     = quantile(family_richness, 0.75),
    max    = max(family_richness),
    IQR    = Q3 - Q1,
    .groups = "drop"
  )
print(stats_week_location, n = Inf)