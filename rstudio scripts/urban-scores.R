# ── 0. Packages ───────────────────────────────────────────────────────────────
library(readxl)
library(dplyr)
library(ggplot2)
library(patchwork)

# ── 1. Load data ───────────────────────────────────────────────────────────────
df <- read_excel("C:/Users/stanv/Desktop/master_project/data/locationchar.xlsx")

# ── 2. Rename columns ─────────────────────────────────────────────────────────
df <- df %>%
  rename(
    pop_density = `GHS_POP_E2025_GLOBE_R2023A_54009_100_V1_0_R3_C19_mean`,
    green_area  = `WVL_2021_005m_03035_V01_R02_mean`,
    IMD_mean    = imperviousnesstotal_mean,
    c0  = `GHS_BUILT_C_MSZ_E2018_GLOBE_R2023A_54009_10_V1_0_R3_C19_0`,
    c1  = `GHS_BUILT_C_MSZ_E2018_GLOBE_R2023A_54009_10_V1_0_R3_C19_1`,
    c2  = `GHS_BUILT_C_MSZ_E2018_GLOBE_R2023A_54009_10_V1_0_R3_C19_2`,
    c3  = `GHS_BUILT_C_MSZ_E2018_GLOBE_R2023A_54009_10_V1_0_R3_C19_3`,
    c11 = `GHS_BUILT_C_MSZ_E2018_GLOBE_R2023A_54009_10_V1_0_R3_C19_11`,
    c13 = `GHS_BUILT_C_MSZ_E2018_GLOBE_R2023A_54009_10_V1_0_R3_C19_13`,
    c14 = `GHS_BUILT_C_MSZ_E2018_GLOBE_R2023A_54009_10_V1_0_R3_C19_14`,
    c23 = `GHS_BUILT_C_MSZ_E2018_GLOBE_R2023A_54009_10_V1_0_R3_C19_23`
  )

# ── 3. Force numeric ──────────────────────────────────────────────────────────
df <- df %>%
  mutate(across(c(pop_density, green_area, IMD_mean,
                  c0, c1, c2, c3, c11, c13, c14, c23), as.numeric))

# ── 4. Filter to 12 locations and add group label ─────────────────────────────
df <- df %>%
  filter(name %in% c(paste0(1:6, "A"), paste0(1:6, "D"))) %>%
  mutate(group = ifelse(grepl("A$", name), "Amsterdam", "Dronten"))

# ── 5. Height-weighted built index ────────────────────────────────────────────
df <- df %>%
  mutate(
    total_pixels          = c0 + c1 + c2 + c3 + c11 + c13 + c14 + c23,
    built_score           = 0*c0 + 0*c1 + 0*c2 + 0*c3 +
      1*c11 + 2*c13 + 3*c14 + 3*c23,
    built_score_per_pixel = built_score / total_pixels
  )

# ── 6. Normalise across ALL 12 samples & compute urban score ──────────────────
norm <- function(x) {
  x   <- as.numeric(x)
  rng <- range(x, na.rm = TRUE)
  if (rng[1] == rng[2]) return(rep(0, length(x)))
  (x - rng[1]) / (rng[2] - rng[1])
}

df <- df %>%
  mutate(
    IMD_norm    = norm(IMD_mean),
    pop_norm    = norm(pop_density),
    green_norm  = 1 - norm(green_area),
    built_norm  = norm(built_score_per_pixel),
    urban_score = 0.35 * IMD_norm +
      0.25 * pop_norm  +
      0.20 * built_norm +
      0.20 * green_norm
  )

# ── 7. Print scores ───────────────────────────────────────────────────────────
df %>%
  select(name, group, urban_score) %>%
  arrange(group, urban_score) %>%
  print(n = Inf)

# ── 8. Colour palette & subsets ───────────────────────────────────────────────
level_colors <- c("#2ecc71", "#a8d08d", "#f9e04b", "#f0a500", "#e05c00", "#c0392b")

sel_A <- df %>%
  filter(group == "Amsterdam") %>%
  mutate(name  = factor(name, levels = paste0(1:6, "A")),
         color = level_colors) %>%
  arrange(name)

sel_D <- df %>%
  filter(group == "Dronten") %>%
  mutate(name  = factor(name, levels = paste0(1:6, "D")),
         color = level_colors) %>%
  arrange(name)

# ── 9. Bar plot helper ────────────────────────────────────────────────────────
make_bar <- function(sel, var, title_txt) {
  ggplot(sel, aes(x = name, y = .data[[var]], fill = name)) +
    geom_col(color = "white", linewidth = 0.3, width = 0.5) +
    geom_text(aes(label = sprintf("%.2f", .data[[var]])),
              vjust = -0.4, size = 2.8) +
    scale_fill_manual(values = setNames(sel$color, as.character(sel$name))) +
    scale_y_continuous(expand = expansion(mult = c(0, 0.2))) +
    labs(x = NULL, y = NULL, title = title_txt) +
    theme_minimal(base_size = 9) +
    theme(
      legend.position  = "none",
      axis.text.x      = element_text(size = 9),
      panel.grid.minor = element_blank(),
      plot.title       = element_text(face = "bold", size = 9)
    )
}

# ── 10. Amsterdam figure ──────────────────────────────────────────────────────
fig_A <- (
  make_bar(sel_A, "IMD_mean",              "Impervious surface (IMD mean)") |
    make_bar(sel_A, "green_area",            "Green area fraction (WVL mean)")
) / (
  make_bar(sel_A, "pop_density",           "Population density (GHS-POP mean)") |
    make_bar(sel_A, "built_score_per_pixel", "Height-weighted built index")
) +
  plot_annotation(
    title   = "Amsterdam — urbanisation levels 1–6",
    caption = "Weights: IMD 35%  ·  Population 25%  ·  Built index 20%  ·  Green area 20%",
    theme   = theme(
      plot.title   = element_text(face = "bold", size = 13),
      plot.caption = element_text(size = 8, color = "grey50")
    )
  )

# ── 11. Dronten figure ────────────────────────────────────────────────────────
fig_D <- (
  make_bar(sel_D, "IMD_mean",              "Impervious surface (IMD mean)") |
    make_bar(sel_D, "green_area",            "Green area fraction (WVL mean)")
) / (
  make_bar(sel_D, "pop_density",           "Population density (GHS-POP mean)") |
    make_bar(sel_D, "built_score_per_pixel", "Height-weighted built index")
) +
  plot_annotation(
    title   = "Dronten — urbanisation levels 1–6",
    caption = "Weights: IMD 35%  ·  Population 25%  ·  Built index 20%  ·  Green area 20%",
    theme   = theme(
      plot.title   = element_text(face = "bold", size = 13),
      plot.caption = element_text(size = 8, color = "grey50")
    )
  )

# ── 12. Print ─────────────────────────────────────────────────────────────────
print(fig_A)
print(fig_D)
