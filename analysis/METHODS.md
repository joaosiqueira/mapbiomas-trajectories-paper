# Time-intensity analysis and components of change — Collection 10

Reference documentation for the analysis in `analysis/`: the published
method it implements, the choices made while implementing it, what the outputs contain,
and what was verified rather than assumed.


---

## 1. The method

### 1.1 Source

Bilintoh, T. M., Pontius, R. G., & Zhang, A. (2024). *Methods to compare sites concerning
a category's change during various time intervals.* GIScience & Remote Sensing, 61(1),
2409484. <https://doi.org/10.1080/15481603.2024.2409484>

The article is Open Access under the Creative Commons Attribution License (CC BY 4.0). The authors also publish an R reference
implementation, `timeseriesTrajectories`, at
<https://github.com/bilintoh/timeseriesTrajectories>.

Applied to MapBiomas Brazil in Fonseca et al. (2026), whose dashboard is `../trajectories.js`.

### 1.2 The problem it solves

A time series of land-cover maps is usually summarised as *net change*: the size of a
category at the start against its size at the end, or a line of its size per year. That
summary hides three things:

- **Gross change.** A category can lose 10 Mha and gain 10 Mha and appear unchanged.
- **Alternation.** A pixel can leave the category and come back. Endpoint comparison
  cannot see it at all, and neither can a series of per-year sizes.
- **Unequal intervals.** Comparing a 5-year interval with a 10-year one without
  annualising makes the longer interval look like faster change.

The method addresses all three: it works on the whole series at once, separates gross
loss from gross gain, annualises by interval duration, and normalises by a denominator
that makes sites comparable.

### 1.3 Unified size — equation 1

The denominator. Three options; the paper recommends the third and this is the one we use:

> **U = the union of the locations where the category exists at any time point.**

Formally `U = Σ_{j=1}^{7} Σ_{m=1}^{Mj} MAXIMUM(Y_jm0, Y_jm1, …, Y_jmT)`. For a binary
presence variable the maximum over time is 1 wherever the category ever occurs, so U is
simply the area that was the category in at least one year. Note the sum runs over
trajectories **1 to 7** — trajectory 8 is "never present" and is excluded by construction.

Why it matters: expressing change as a percentage of U rather than of the study area lets
you compare a class that covers half the country with one that covers 0.5% of it. For
Brazil, collection 10:

| class | unified size (Mha) |
|---|---|
| forest_formation | 481.1 |
| pasture | 245.1 |
| savanna_formation | 168.9 |
| agriculture | 80.4 |
| grassland | 40.0 |
| wetland | 32.6 |
| river_lake_and_ocean | 30.4 |
| urban_area | 4.6 |

For every class, `U + area(trajectory 8) = 850.7 Mha`, Brazil's area — a useful check.

**A label in the paper that looks like a contradiction, and is not.** The axis drawn
inside Figure 4 reads *"Annual Change (% of region)"*, which appears to name a different
denominator. It does not. The caption of that same figure says "expressed as the annual
percentage of the unified size"; the body text introducing it says "the vertical axis is
the annual gross change as a percentage of the unified size"; and the introduction argues
at length *against* reporting change as "a percentage of an arbitrary region of the
database's spatial extent", calling the unified size the "relevant constant region" that
should replace it. The drawn label uses "region" in that sense, or is stale artwork.
Our `Annual change (% of unified size per year)` follows the text, so there is nothing to
reconcile — but the label will be noticed by anyone reading Figure 4 next to our figures,
which is why it is written down here.

### 1.4 The eight trajectories — Table 2 of the paper

Each pixel is assigned exactly one trajectory over the whole temporal extent. `Y_jmt` is
the presence (0 or 1) of the category in trajectory `j`, cell `m`, at time `t`; `T` is the
final time point.

| id | name | definition | colour |
|---|---|---|---|
| 0 | Mask | eliminated from computation | `#ffffff` |
| 1 | Loss without Alternation | `Y_m0 > Y_mT` and `Y_mt-1 ≥ Y_mt` for all t | `#941004` dark red |
| 2 | Gain without Alternation | `Y_m0 < Y_mT` and `Y_mt-1 ≤ Y_mt` for all t | `#020e7a` dark blue |
| 3 | Loss with Alternation | `Y_m0 > Y_mT` and `Y_mt-1 < Y_mt` for at least one t | `#f5261b` light red |
| 4 | Gain with Alternation | `Y_m0 < Y_mT` and `Y_mt-1 > Y_mt` for at least one t | `#14a5e3` light blue |
| 5 | All Alternation Loss First | `Y_m0 = Y_mT` and loss is the first change | `#8b8000` dark yellow |
| 6 | All Alternation Gain First | `Y_m0 = Y_mT` and gain is the first change | `#ffff00` light yellow |
| 7 | Stable Presence | `Y_mt-1 = Y_mt > 0` for all t | `#666666` dark grey |
| 8 | Stable Absence | `Y_mt-1 = Y_mt = 0` for all t | `#cfcfcf` light grey |

Read structurally: **odd ids start present, even ids start absent**; 1 and 2 have exactly
one change; 3 and 4 have an odd number of changes greater than one; 5 and 6 have an even
number of changes, so they end where they started; 7 and 8 have no change at all.

Our implementation assigns these ids with the same rules and the same colours — see
§2.3. The colours are not a local choice and must not be changed.

### 1.5 Gross loss and gross gain — equations 2 to 5

Per trajectory `j` and interval `t`, annualised and normalised:

```
L_jt = [ Σ_m MINIMUM(0, Y_jmt − Y_jmt−1) ] / (U · d_t)      ≤ 0     (eq 2)
G_jt = [ Σ_m MAXIMUM(0, Y_jmt − Y_jmt−1) ] / (U · d_t)      ≥ 0     (eq 3)
```

`d_t` is the interval duration in years, which is what makes intervals of different
lengths comparable. Summed over the extent, again weighted by duration:

```
Loss = [ Σ_{j=1}^{6} Σ_t (L_jt · d_t) ] / Σ_t d_t                   (eq 4)
Gain = [ Σ_{j=1}^{6} Σ_t (G_jt · d_t) ] / Σ_t d_t                   (eq 5)
```

The sums stop at `j = 6` because trajectories 7 and 8 never change. These two values are
the **dashed horizontal lines** in the figures.

### 1.6 The three components — equations 6 to 9

```
Net         = Loss + Gain                                            (eq 6)
Quantity    = |Net| = |Σ_{j=1}^{4} Σ_m (Y_jmT − Y_jm0)| / (U · Σ d_t)   (eq 7)
Exchange    = [ Σ_{j=1}^{4} Σ_m |Y_jmT − Y_jm0| ] / (U · Σ d_t) − Quantity  (eq 8)
Alternation = Gain − Loss − Exchange − Quantity                      (eq 9)
```

In words, from the paper:

- **Quantity** — the absolute net change between the first and the last time point. The
  legend says *Quantity Loss* or *Quantity Gain* depending on the sign of `Net`.
- **Exchange** — simultaneous gain at some locations and loss at other locations between
  the first and last time point. It is large when trajectories 1 and 2 have similar
  areas: the category moved without changing size.
- **Alternation** — pairs of gain and loss at *one* location through the series. It is
  the part of gross change that endpoint comparison cannot see, and it exists only with
  three or more time points.

The three sum to the total gross change, `Gain − Loss`. That identity is what `eq 9` makes
explicit and what our `checkComponents` enforces.

**A shortcut worth knowing.** Trajectories 1–4 have known endpoints — 1 and 3 run presence
to absence, 2 and 4 absence to presence — so the cell sums in equations 7 and 8 collapse
into trajectory areas:

```
Quantity = | A₂ + A₄ − A₁ − A₃ | / (U · D)
Exchange = ( A₁ + A₂ + A₃ + A₄ ) / (U · D) − Quantity
```

where `A_j` is the area of trajectory `j` and `D = Σ d_t`. Equivalently
`Exchange = 2·min(endpoint gain, endpoint loss) / (U · D)`. This is why the decomposition
needs **no extra Earth Engine run**: the trajectory areas are already exported.


**Worked example — forest formation in Brazil.** The three components are easier to hold
onto with numbers attached. Over 1985–2024, forest formation has a unified size of
481.1 Mha.

*Comparing only the first and last maps:* 76.5 Mha of forest are gone and 11.8 Mha are
new.

- **Quantity = 64.7 Mha**, the difference `76.5 − 11.8`. How much the category actually
  shrank — the one number a two-map subtraction would give you. It is labelled *Quantity
  Loss* here because the balance is negative; for pasture and agriculture the label
  becomes *Quantity Gain*.
- **Exchange = 23.6 Mha**, or `2 × 11.8`. Wherever 11.8 Mha of new forest appeared, an
  equal amount was lost somewhere else to offset it: the category **moved** without
  changing size. The factor of two is there because both the loss and the gain are real
  gross change — two hectares disturbed for each hectare relocated.

Those two sum to 88.3 Mha, which is exactly `76.5 + 11.8`: all the change a two-point
comparison can see.

*Looking at the whole series:*

- **Alternation = 65.2 Mha**, everything the two maps cannot show — gain and loss at the
  **same** place through the series. A pixel that left and came back. With only two time
  points it is invisible by construction.

```
total gross change   153.6 Mha
  ├─ Quantity         64.7   how much it shrank
  ├─ Exchange         23.6   it moved
  └─ Alternation      65.2   it left and came back
```

So **42% of Brazil's forest change is alternation**, nearly as much as the net loss
itself. A two-map analysis would report 64.7 Mha and miss 88.9 Mha of change that really
happened.

**The three signatures.** Each class has a characteristic mix, and the mix is the
diagnosis:

| class | Quantity | Exchange | Alternation | what it says |
|---|---|---|---|---|
| urban_area | **90%** | 0% | 10% | grows and does not go back |
| agriculture | 43% | 7% | 50% | expands, with much rotation |
| forest_formation | 42% | 15% | 42% | shrinks, and churns |
| grassland | 1% | 13% | **86%** | size nearly stable, large oscillation |
| wetland | 3% | 4% | **92%** | almost all of it is back and forth |

Urban area is the clean case: 2.8 Mha gained, **zero** lost. With nothing to cancel,
almost everything is Quantity.

Grassland is the opposite: 9.4 Mha lost and 7.8 Mha gained, a net of only 1.6 — but 86%
alternation. A chart of "grassland area per year" would suggest that almost nothing
happened.

**Alternation measures reversal, not its cause.** Wetland at 92% is plausibly real —
floodplains flood and dry. Grassland at 86% mixes genuine dynamics with classification
confusion against pasture and savanna, which manifests in exactly this way. The method
raises the question; answering it means looking at the data.

### 1.7 How to read the two figures

**Panel (a) — change per interval** (Figure 4 of the paper):

- vertical axis: annual gross change as a percentage of the unified size;
- gains rise above the axis, losses drop below;
- colour within a stack: the pixel's trajectory over the **whole** extent, not the
  interval's own trajectory — so the same colour means the same thing in every bar;
- the vertical span from the top of the gain to the bottom of the loss is the **speed**
  of change in that interval;
- bar **width** is the interval duration, so bar **area** is the amount of change;
- the dashed lines are Gross Gain and Gross Loss averaged over the extent (eq 4 and 5).

**Panel (b) — components of change** (Figure 5 of the paper): one stacked bar covering
all intervals, split into Quantity, Exchange and Alternation, in the same units as panel
(a). Greys, deliberately outside the trajectory palette so the two panels cannot be
confused.


### 1.8 Why the same colour appears above and below the axis

The colour of a segment is the pixel's **trajectory**; the side of the axis is the
**direction of the event** in that interval. The two are independent, so most colours
appear on both sides — and that is not a defect, it follows from the definitions.

A trajectory with alternation necessarily contains both losses and gains. A pixel of
trajectory 3, `Presence → Alternation → Loss → Absence`, left the category and came back
one or more times before finally going. Its gains are drawn above the axis and its losses
below, both in trajectory 3's colour.

Only trajectories 1 and 2 are one-sided, because they have exactly one change each:

| traj | | gain | loss | side |
|---|---|---|---|---|
| 1 | Loss without Alternation | — | 2.959 | **below only** |
| 2 | Gain without Alternation | 0.419 | — | **above only** |
| 3 | Loss with Alternation | 0.339 | 0.651 | both |
| 4 | Gain with Alternation | 0.207 | 0.113 | both |
| 5 | All Alternation Loss First | 0.527 | 0.513 | both |
| 6 | All Alternation Gain First | 0.397 | 0.411 | both |

*(Brazil, forest formation, %/yr of the unified size, 5-year grid.)*

This is the ten-composite rule seen from the figure's side: `traj 1 → {11}`,
`traj 2 → {22}`, and every other trajectory `→ {1x, 2x}`.

The paper does the same. Its Figure 7(a) legend has four entries, and both yellows — the
two alternation trajectories — appear above and below the axis, while dark blue appears
only above and dark red only below.

The alternative would be a colour per composite, ten instead of six. But then colour would
stop answering "what did this pixel do over forty years", which is the question the figure
exists for. Keeping it as is also makes a real reading possible: **light red above the
axis** means forest gains that happened on pixels which, over 1985–2024, ended up lost —
regrowth that did not hold.

### 1.9 What the numbers count: events, not pixels

For each interval the method sums **events per pixel**, weighted by area:

```
gross loss = Σ pixel area × (number of 1→0 transitions in the interval)
gross gain = Σ pixel area × (number of 0→1 transitions in the interval)
```

So the same pixel can be counted more than once, in three ways:

1. **On both sides of the same bar.** A pixel that lost in 1997 and regained in 1999
   enters both sums for 1995–2000.
2. **Twice on the same side of one bar.** Lost, regained, lost again inside one interval.
3. **In several bars.** The ordinary case for any alternating trajectory.

Measured for trajectory 3, forest formation, over the 2°×2° window
`ee.Geometry.Rectangle([-48.0, -12.0, -46.0, -10.0])` in the Cerrado, at native 30 m,
covering 242 587 pixels of that trajectory. It reads the `annual_events` asset directly,
so it can be reproduced from `statistics/annual_events.py` without the exported tables:

| interval | loss **and** gain in the same interval | 2+ events on one side |
|---|---|---|
| 1985-1990 | 0.86% | 0.02% |
| 1990-1995 | 1.62% | 0.02% |
| 1995-2000 | **4.40%** | 0.02% |
| 2000-2005 | 2.93% | 0.01% |
| 2005-2010 | 3.60% | 0.03% |
| 2010-2015 | 2.65% | 0.02% |
| 2015-2020 | 2.72% | 0.03% |
| 2020-2024 | 1.18% | 0.01% |

Within a single 5-year interval, then, double counting touches 1–4% of that trajectory's
pixels. *Across* intervals it is the rule rather than the exception — having at least one
alternation somewhere in the series is what defines trajectories 3 to 6.

**This is the intended measurement**, not an artefact: the method asks how much transition
occurred, and a pixel that oscillated three times did produce three transitions. But two
consequences have to be carried into any reading of the results.

**The total can exceed 100% of the unified size.** Wetland in Brazil runs at 10.6%/yr,
which over 39 years is 413% of its unified size. The same ground changed repeatedly.

**The column is not an area of land.** It is named `gross change (hectare)` rather than
`area (hectare)` for that reason. Anyone summing it expecting "hectares of forest lost"
gets an inflated number. For actual area — how much ground changed state between 1985 and
2024 — the right figure is panel (b): `Quantity` measures the net difference between the
endpoints, and there each pixel counts once.

---

## 2. The implementation

### 2.1 Pipeline

```
MapBiomas C10 LULC  (public asset, 40 bands, 1985-2024)
        │
        │  statistics/annual_events.py  — paper classRemap, presence stack
        ▼
statistics/mapbiomas_brazil_annual_events_to_asset.py        8 GEE tasks
        │   one image per class: trajectories_1985_2024 + 39 event bands
        ▼
statistics/mapbiomas_brazil_export_statistics_time_intensity.py   16 GEE tasks
        │   composite = event×10 + base trajectory, crossed with territories
        ▼   one GeoJSON per class × territory, numerator and denominator together
download the GeoJSON files from Cloud Storage into data/JSON/
        ▼
notebooks/scripts/mapbiomas_brazil_time_intensity_tables.py  2 xlsx
notebooks/scripts/mapbiomas_brazil_time_intensity_figures.py 56 A4 figures + 7 components-by-class + captions.txt
```

Run times observed for collection 10: the 8 asset exports took 1h20 to 2h43 each; the 16
statistics exports 20 to 30 minutes each. Everything after the download is local and takes
under a minute.

### 2.2 Class definition

The time-intensity pipeline uses the **paper's flat `classRemap`** (in
`statistics/config.py`), which folds the 49 collection 10 classes into about 30:
`5, 6, 49 → 3` (forest formation), `63 → 12` (grassland), every crop subtype `→ 18`
(agriculture).

This is deliberately **not** the level 1–4 legend hierarchy the other collection 10
products use. Two reasons:

1. The annual events and the base trajectory must share one definition of "presence". If
   they disagree, impossible composites appear (§2.4).
2. It is the definition behind the published paper asset, so the numbers stay comparable
   with Fonseca et al. (2026).

Eight classes are analysed: `forest_formation` (3), `savanna_formation` (4), `wetland`
(11), `grassland` (12), `pasture` (15), `agriculture` (18), `urban_area` (24),
`river_lake_and_ocean` (33).

### 2.3 Trajectory assignment

`annual_events.baseTrajectory()` builds the 1–8 code with a chain of `.where()` calls in a
fixed order. **Order matters**: later calls overwrite earlier ones, so reordering silently
changes the classification of pixels that satisfy more than one condition. The order is
1, 2, 3, 4, 5, 6, 7, 8 and is asserted by the selftest on both the Python and the
Code Editor twin.

`annual_events.annualEvents()` emits 39 bands, one per consecutive year pair: `0` no
change, `1` loss, `2` gain. Left unmasked on purpose — the statistics step masks on the
per-interval count, and a masked zero would fight that.

**Scope: the trajectory belongs to the whole extent, never to an interval.** It is
computed once, from all 40 years — `baseTrajectory()` reads `bands[0]` (1985),
`bands[-1]` (2024) and `countRuns()` over the entire stack, and the band is named
`trajectories_1985_2024` — and it enters the interval statistics only as a grouping key.
`maskedEventArea` varies the interval mask and the event offset; the trajectory it groups
by is the same image every time. **The interval says *when* a gain or loss happened; the
trajectory says what that pixel did across 1985–2024.**

It could not work the other way. Across a single annual transition a pixel has exactly one
event or none, so *alternation is undefined at that scale* — a trajectory that mentions
alternation only means something over a series. The ten-composite rule of §2.4 is the same
fact stated structurally: it holds only because the units digit is full-extent.

The denominator shares that scope. The unified size is computed once over 1985–2024
(`grid == 'base'`) and is constant across every bar of every grid, which is what makes bar
heights comparable between intervals, between classes and between territories.

The visible consequence is §1.8: the same colour appears above and below the axis, because
one pixel of an alternating trajectory contributes a gain in one interval and a loss in
another. Note that this is also how the paper's own Figure 4 behaves — *All Alternation
Gain First* sits above the axis in 2000–2001 and below it in 2001–2002.

---

## 3. Outputs

### 3.1 Tables

`data/TABLES/brazil-time-intensity-c10-{5y,10y}-1a.xlsx`, six sheets each.

**`intensity`** — the tidy table the figures are drawn from. One row per territory ×
class × interval × composite.

| column | meaning |
|---|---|
| `territory`, `category`, `feature_id` | Brasil or one of the six biomes |
| `class_name`, `class_id`, `level_id` | one of the eight classes |
| `grid`, `period`, `year_start`, `year_end`, `duration_years` | the interval |
| `composite_id`, `event_id`, `event` | the composite and its loss/gain digit |
| `trajectory_id`, `trajectory_label_en`, `color` | the base trajectory |
| `gross change (hectare)` | change accumulated in the interval — see the warning below |
| `unified_size_ha` | the denominator, U |
| `annual_area_ha_per_year` | `gross change / duration_years` |
| `pct_of_unified_per_year` | `100 × annual / U` — **the vertical axis** |
| `pct_signed` | the same, negative for loss, for plotting |

> **`gross change (hectare)` is not an area of land.** A pixel that flips twice inside an
> interval is counted twice, and the same pixel can appear on both sides of one bar. It is
> a quantity of change, and per-interval sums can exceed the unified size. See §1.9, which
> measures how often this happens. For area, use `Quantity` in the `components` sheet.

**Layout note.** Both panels carry their legend **below the axes**, frameless, and are
labelled `(a)` and `(b)` outside the axes; the class and territory go in the figure
title. Below, not inside: a legend over the plot either covers data or has to be given
headroom, and the headroom it needs is class-dependent — wetland's axis reaches 12.5%/yr
where forest formation's reaches 0.8%/yr, so no single fraction serves both. With the
legend outside, the vertical limits follow the data alone and the bars fill the panel.
They are still **asymmetric**, since gains and losses are rarely the same size.

Territory names are the English ones MapBiomas publishes, in `config.TERRITORY_NAMES`.
They are not read from the theme asset: its `NAME` column is Portuguese despite the
name, identical to `NAME_PT_BR`.

**`intensity_wide`** — the same values pivoted so each period is a column. For reading,
not for computing.

**`unified_size`** — area per base trajectory 1–8 per territory and class. The
denominator is the sum of 1–7; trajectory 8 is included in the sheet so the total is
auditable against the territory's area.

**`averages`** — gross gain and gross loss over 1985–2024 (eq 4 and 5), the dashed lines,
plus net and total change.

**`components`** — Quantity, Exchange and Alternation per territory and class (eq 7–9),
with `quantity_direction` saying whether the net change was a gain or a loss, and the
endpoint gain/loss areas the decomposition was computed from.

**`legend`** — the ten composites with event, base trajectory, bilingual labels and colour.

### 3.2 Figures

```
data/FIGURES/captions.txt                                      every caption, as running text
data/FIGURES/{territory}/
    components-by-class-{territory}-v1.png
data/FIGURES/{territory}/{grid}/
    time-intensity-a4-trajectories-{free|sharedy}-{grid}-{territory}-v1.png
    time-intensity-a4-components-{free|sharedy}-{grid}-{territory}-v1.png
```

7 territories × 2 grids × 2 figures × 2 y-axis versions = 56 grid figures, plus 7
components-by-class figures = **63 PNG files** at 300 dpi, about 11 MB, roughly 17 seconds
to build.

**The components-by-class figure.** One axes per territory, every class a column, the
three components stacked, about 155 × 90 mm. It answers a question the eight separate
panels cannot: *which class changes fastest, and of what is that change made*. That
comparison is the reason the unified size is the denominator — each class is divided by
its own U, so a class covering half the country sits on the same axis as one covering
0.5% of it. For Brazil it puts wetland at 10.6 %/yr against forest formation's 0.8, and
shows that almost all of wetland's change is Alternation while nearly all of urban area's
is Quantity.

The cost is the same one the `sharedy` grid figures pay: on a single linear axis the
slow classes become thin bands. That is the honest reading rather than a defect, and the
source figure this was modelled on has the same property.

A letter over each column — `L` or `G` — gives the side the Quantity component falls on,
from `quantity_direction`. It replaces the per-panel `All intervals, net loss` label,
which cannot be repeated eight times across one axis without crowding it; the caption
explains the letter.

**It is written once per territory, not once per (territory, grid).** The components use
the whole 1985–2024 extent, so they do not depend on the interval grid at all. Drawn
inside the grid loop, as the per-panel components figure still is, the 5y and 10y files
come out **byte-identical** — verified with `md5`. That is harmless duplication in the
grid figures, whose file names at least say which grid they came from, but it would be
actively misleading in a figure whose caption says "all intervals".

**Two figures, not one.** The pair does not fit an A4 page at a legible size, so the
coloured charts and the grey decomposition are separate, each holding the eight classes in
two columns by four rows and lettered `(a)` to `(h)`. Cell positions match between them,
so panel (c) is the same class in both.

Both are built to the A4 text block, at most 170 × 240 mm at 300 dpi — currently about
150 × 224 mm and 148 × 182 mm. Nothing enforces that, so measure again after a layout
change. `bbox_inches='tight'` widens the saved image to whatever it contains, which is how
a four-column legend once pushed the figure to 184 mm without any warning.

**No title and no caption on the figure.** The journal sets both as running text, so the
captions go to `captions.txt` and each is self-contained: it names the territory, the
interval grid and the meaning of every element, since there is no title to lean on.

`FIGURE_MODES` is `('complete',)`. Two other modes exist and are off: `'panel'`, the
pre-A4 large grid, now redundant; and `'single'`, one figure per class.

`FORMATS` is PNG only. The vector PDF is the slow half of the build and doubles the file
count; add `'pdf'` back when a submission needs it.

`FOLDER_BY_TERRITORY` and `FOLDER_BY_GRID` each turn a directory level off. The file names
carry the territory and the grid regardless, so a figure pulled out of the tree and sent on
its own is still self-describing.

#### Layout decisions worth keeping

**No horizontal gridlines.** The two reference lines are black and told apart by dash
pattern — dash-dot for gross gain, dotted for gross loss. That survives greyscale printing
and stops them competing with the trajectory palette.

**The legend sits below the axes**, in four columns, sized to fit inside the figure width.
Below rather than inside: a legend over the plot either covers data or needs headroom, and
the headroom it needs is class-dependent — wetland's axis reaches 12.5%/yr where forest
formation's reaches 0.8%/yr, so no single fraction serves both. With it outside, the
vertical limits follow the data alone and the bars fill the panel. They remain
**asymmetric**, since gains and losses are rarely the same size.

**`ROW_SPACING` is per figure type**, 0.40 for the coloured figure and 0.62 for the grey
one, as a fraction of panel height. The two have different things hanging below the axes —
tick labels in one, an x label in the other — so one value cannot serve both. Too small and
the row above collides with the title of the row below, which is invisible in a thumbnail;
`selftest_pipeline.rowClearance` measures the gap in both figures and fails under 4 px.
Currently 12 px and 17 px.

The grey panels label their x axis `All intervals, net loss` on **one line**. Two lines
reach far enough down to overlap the title of the row below. The label carries the
direction because a shared legend cannot: Quantity is a loss for forest formation and a
gain for agriculture.

**Typography.** `plots.usePaperStyle()` sets the figures in the paper's face: Palatino at
10 pt, black. "Palatino Linotype" is the Microsoft name for it; macOS ships the same face
as "Palatino" and Linux as "P052" or "URW Palladio L", so `PAPER_FONTS` lists all of them
and falls back to a generic serif. `pdf.fonttype` is 42, which embeds the face rather than
relying on the reader to have it — verified with `pdffonts`.

**Trajectory names are the paper's Table 2 names** — *Loss without Alternation* and so on.
The arrow form that spells out the sequence survives as `path_en` in the code book and as
the `trajectory_path` column in the tables: it explains what the name means but is too long
for a legend entry.

**Class names follow the paper**, not the MapBiomas legend: *Cropland* where MapBiomas says
agriculture, *Water* where it says river, lakes and oceans. The equivalence is stated once
in the caption rather than repeated inside two of the eight panel titles.

**Two y-axis versions, `free` and `sharedy`.** They answer different questions and neither
substitutes for the other, so both are written rather than one being chosen.

With a *free* axis each panel is scaled to fill itself, which shows how a class changed
through time. Heights are then not comparable between panels: urban area's gains are
enormous relative to its small unified size while forest formation's are a fraction of a
percent per year.

With a *shared* axis every panel carries the same scale, which shows which class changes
more. For Brazil that scale runs to about ±7.5%/yr, set by wetland, and forest formation
becomes a thin band — that is the finding, not a defect, but it costs the small classes
their detail. `sharedLimits` computes the range across the classes in the figure, not
across territories; a cross-territory version would need that scope widened.

The caption states which version it belongs to, since the figures are otherwise identical.

---

## 4. Results for collection 10, Brazil

Annual change as a percentage of each class's unified size, 1985–2024.

| class | gross gain | gross loss | Quantity | Exchange | Alternation | total | Alternation share |
|---|---|---|---|---|---|---|---|
| forest_formation | 0.237 | 0.581 | 0.345 *loss* | 0.126 | 0.348 | 0.818 | 42% |
| savanna_formation | 0.694 | 1.262 | 0.567 *loss* | 0.292 | 1.096 | 1.956 | 56% |
| wetland | 5.117 | 5.484 | 0.367 *loss* | 0.443 | 9.792 | 10.601 | 92% |
| grassland | 3.890 | 3.992 | 0.102 *loss* | 1.001 | 6.779 | 7.883 | 86% |
| pasture | 2.167 | 1.511 | 0.656 *gain* | 0.820 | 2.202 | 3.678 | 60% |
| agriculture | 2.347 | 0.943 | 1.404 *gain* | 0.231 | 1.656 | 3.291 | 50% |
| urban_area | 1.618 | 0.089 | 1.529 *gain* | 0.006 | 0.172 | 1.707 | 10% |
| river_lake_and_ocean | 3.069 | 3.349 | 0.281 *loss* | 0.458 | 5.679 | 6.418 | 88% |

Forest formation's loss per interval peaks at 0.758%/yr in 2000–2005, falls to 0.373%/yr
in 2010–2015 and rises again to 0.558%/yr in 2020–2024, reproducing the known Brazilian
deforestation curve. Gross gain stays between 0.20 and 0.26%/yr throughout.

**Alternation share by biome**, as a percentage of each cell's total gross change:

| class | Amazon | Caatinga | Cerrado | Atlantic Forest | Pampa | Pantanal |
|---|---|---|---|---|---|---|
| forest_formation | 38 | 65 | 48 | 43 | 74 | 59 |
| savanna_formation | 63 | 55 | 55 | 59 | — | 72 |
| wetland | 85 | 80 | 38 | 68 | 87 | 96 |
| grassland | 76 | 64 | 13 | 51 | 70 | 93 |
| pasture | 47 | 72 | 61 | 65 | 87 | 40 |
| agriculture | 38 | 49 | 37 | 60 | 73 | 81 |
| urban_area | 15 | 14 | 10 | 8 | 7 | 4 |
| river_lake_and_ocean | 90 | 90 | 67 | 79 | 80 | 90 |

### Reading these numbers with care

**Urban area behaves as physical reasoning predicts**: Alternation is 4–15% everywhere,
Quantity dominates, and the direction is gain. Cities grow and do not un-grow. The paper
makes the same point in reverse, noting that high Alternation in a category such as urban
would indicate poor data quality rather than real dynamics. Our figure is low, which is
reassuring about the pipeline as a whole.

**Water and wetland alternating 80–96% is plausibly real.** Rivers, lakes and flooded
areas genuinely appear and disappear between years.

**Grassland at 86% nationally deserves scrutiny.** Some of it is real, but grassland is
also a class that classification confuses with pasture and savanna, and alternation is
exactly how confusion manifests. The Cerrado figure of 13% against Pantanal's 93% is a
large spread for one class and is worth investigating before it is interpreted as ecology.

**Alternation is not noise by definition, and not signal by definition.** It measures
reversal. Whether a given reversal is a wet season, a fallow, a regrowth cycle or a
misclassification is a question this method poses rather than answers.

---

## 5. What was verified

Without GEE credentials, by `notebooks/scripts/selftest_time_intensity.py` (stdlib only)
and `selftest_pipeline.py` (needs the venv):

- **The ten-composite rule**, by exhaustive enumeration of 131 068 binary series.
- **Grid tiling**: each grid sums to exactly 39 transitions, no overlap, no gap.
- **Grid equivalence**: both grids give identical per-composite totals.
- **The area identity**, asserted on the actual matplotlib patches:
  `Σ(width × height)` over the gain bars equals the total gain over the extent. This is
  the property that lets the figure be read as "area = amount of change".
- **Bars tile the axis** from 1985 to 2024 with no gap or overlap, and every patch colour
  is one of the eight canonical hexes.
- **JS/Python parity**: the Code Editor twin is parsed and compared against `config.py` on
  years, class list, the 49-class remap and the order of the trajectory rules. Verified to
  fail on three injected regressions.

Against the live Earth Engine API:

- The collection 10 asset has exactly 40 bands, `classification_1985` … `classification_2024`.
- **Our base trajectory agrees with two independently produced assets on 100.0000% of
  pixels** at native 30 m, for forest formation, agriculture and pasture: the published
  `lulc_trajectories_per_class_col10` and `nexgenmap/MapBiomas_TOOLs/Trajectories/Trajs_image_col10`.
  This validates the `classRemap` transcription and the trajectory rules end to end.
- On real pixels: events per pixel equal `number_of_changes`; `losses − gains` equals
  `presence(t₁) − presence(t_T)`; no impossible composite appears.

On the real output:

- The two grids agree to 0.000004 ha.
- `Σ(duration × rate)/39` equals the dashed-line average to 1e-10 percentage points, for
  all 55 territory × class combinations.
- The three components sum to the total gross change to 9e-16 percentage points.
- `U + area(trajectory 8)` equals Brazil's area, 850.7 Mha, for every class.

---

## 6. Things that bit us

Recorded because none of them would be caught by reading the code.

**`ee` calls at module level run before the caller can initialize.** `PIXEL_AREA` was a
module-level constant calling `ee.Image.pixelArea()`, which executed at *import* — before
any `ee.Initialize()` in the importing script. It is now the function `pixelArea()`. The
selftest has an AST check that distinguishes import-time code from function bodies.

**Shadowing a loop variable renames your files.** Naming a gridspec `grid` shadowed the
interval-grid name, and the figures collapsed to half their number with `GridSpec(...)`
in their filenames.

**Both the value band and the group-key band must be masked** before a grouped
`reduceRegion`. Masking only the value band makes every unchanged pixel emit a group with
sum zero, including impossible composites.

---

## 7. Provenance

| thing | where |
|---|---|
| LULC input | `projects/mapbiomas-public/assets/brazil/lulc/collection10/mapbiomas_brazil_collection10_coverage_v2` |
| territory layers | `projects/mapbiomas-workspace/AUXILIAR/ESTATISTICAS/COLECAO8/VERSAO-1` (`country-raster`, `refined_biome-raster`) |
| published paper asset | `projects/mapbiomas-public/assets/papers/fonseca_et_all_2026/lulc_trajectories_per_class_col10` |
| intermediate assets, GeoJSON | written to a project and bucket of your own — see `statistics/config.py` |

`ASSET_THEMES` points at the **collection 8** territory set because no collection 10 set
has been published. Territory boundaries move little between collections. Repoint it when
one is.

The published paper asset's bands are `traj_for, traj_pas, traj_sav, traj_gra, traj_wat,
traj_urb, traj_agr, traj_wet` — **not** the `forest, pasture, …` names the paper script
uses in memory. `config.PUBLISHED_BAND_BY_CLASS` maps them.
