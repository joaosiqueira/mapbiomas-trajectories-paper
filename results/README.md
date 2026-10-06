# Results

The final tables and figures of the time-intensity analysis, Collection 10, 1985–2024. Code
that produced them: [`../analysis/`](../analysis/README.md). Method and equations:
[`../analysis/METHODS.md`](../analysis/METHODS.md).

These are the files as built, version `v1`; they are replaced, not accumulated, when the
analysis is rerun.

## Conventions

- **Classes (8):** forest formation (3), savanna formation (4), wetland (11), grassland
  (12), pasture (15), agriculture/cropland (18), urban area (24), river, lake and ocean
  (33), referred to in the figures as *Cropland* and *Water*.
- **Territories (7):** Brazil and the six biomes — Amazon, Caatinga, Cerrado, Atlantic
  Forest, Pampa, Pantanal.
- **Interval grids:** `5y` = 1985–1990, …, 2015–2020, 2020–2024; `10y` = 1985–1995,
  1995–2005, 2005–2015, 2015–2024. Both tile the 39 annual transitions; the last interval
  is shorter on purpose.
- **Unified size (U):** the area where a class occurs in at least one year. Every change is
  expressed as a percentage of its class's U per year, so classes of very different size
  share one axis.
- **Trajectories (TR1–TR8):** Table 2 of Bilintoh, Pontius & Zhang (2024), computed over
  the whole 1985–2024 extent.

| TR | Name | Path |
|---|---|---|
| 1 | Loss without Alternation | Presence → Loss → Absence |
| 2 | Gain without Alternation | Absence → Gain → Presence |
| 3 | Loss with Alternation | Presence → Alternation → Loss → Absence |
| 4 | Gain with Alternation | Absence → Alternation → Gain → Presence |
| 5 | All Alternation Loss First | Presence → Alternation → Presence |
| 6 | All Alternation Gain First | Absence → Alternation → Absence |
| 7 | Stable Presence | Presence → Stable → Presence |
| 8 | Stable Absence | Absence → Stable → Absence |

## Tables — `tables/`

`brazil-time-intensity-c10-5y-1a.xlsx` and `brazil-time-intensity-c10-10y-1a.xlsx`, one per
interval grid, six sheets each.

| sheet | content |
|---|---|
| `intensity` | the tidy table the figures are drawn from: one row per territory × class × interval × composite. Main columns: `territory`, `class_name`, `period`, `year_start`, `year_end`, `duration_years`, `event` (loss or gain), `trajectory_id`, `trajectory_label_en`, `gross change (hectare)`, `unified_size_ha`, `annual_area_ha_per_year`, `pct_of_unified_per_year` (the vertical axis), `pct_signed` |
| `intensity_wide` | the same values with one column per period, for reading |
| `unified_size` | area per base trajectory 1–8 per territory and class; U is the sum of 1–7, and 8 is kept so the total can be audited against the territory area |
| `averages` | gross gain and gross loss over 1985–2024 (equations 4 and 5, the dashed lines in the figures), plus net and total change |
| `components` | Quantity, Exchange and Alternation per territory and class (equations 7–9), the direction of the net change and the endpoint gain and loss they were computed from |
| `legend` | the ten (event, trajectory) composites with labels and colours |

> **`gross change (hectare)` is not an area of land.** It counts transitions: a pixel that
> flips twice in an interval counts twice, and the same pixel can appear as both gain and
> loss in one bar. Per-interval sums can therefore exceed the unified size. For the area
> that actually changed state between 1985 and 2024, use `Quantity` in `components`.

## Figures — `figures/`

63 PNG files at 300 dpi, sized for an A4 text block (at most 170 × 240 mm), plus
`captions.txt` with the full caption of every figure — the figures carry neither title nor
caption, since both are set as running text in the paper.

```
figures/captions.txt
figures/<territory>/components-by-class-<territory>-v1.png
figures/<territory>/<grid>/time-intensity-a4-<type>-<yaxis>-<grid>-<territory>-v1.png
```

`<territory>` is `brazil`, `amazon`, `caatinga`, `cerrado`, `atlantic-forest`, `pampa` or
`pantanal`.

| figure | what it shows | how to read it |
|---|---|---|
| `time-intensity-a4-trajectories-*` (Figure 4 of the method paper) | one panel per class, eight panels (a)–(h): annual gross change per interval | gains above the axis, losses below; bar width is the interval duration, so bar **area** is the amount of change; colour is the pixel's trajectory over the whole series; dashed lines are the 1985–2024 average gross gain and loss |
| `time-intensity-a4-components-*` (Figure 5) | the same eight panels, one bar each | the total gross change decomposed into **Quantity** (net change between first and last year), **Exchange** (gain here paired with loss elsewhere between those same years) and **Alternation** (gain and loss at one location through the series, invisible to a two-date comparison). The three sum to the total |
| `components-by-class-*` | one axis, eight columns | all classes side by side on a common scale; the letter above a column is the direction of the net change, **L** for loss and **G** for gain. Independent of the interval grid |

`<yaxis>` is `free` or `sharedy`. With `free`, each panel is scaled to fill itself, which
shows how a class changed through time; heights are not comparable between panels. With
`sharedy`, all panels share one scale, which shows which class changes more, at the cost of
detail in the slow classes.

Why the same colour appears above and below the axis, and why bars can exceed 100 % of the
unified size over the whole period, are explained in
[`METHODS.md` §1.8–1.9](../analysis/METHODS.md).
