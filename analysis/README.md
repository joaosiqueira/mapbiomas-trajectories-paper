# Analysis: time-intensity tables and figures

Code that produces the tables and figures in [`../results/`](../results/README.md): the
*time intensity* analysis of Bilintoh, Pontius & Zhang (2024) applied to MapBiomas Brazil
Collection 10 (1985–2024), for eight land cover classes, Brazil and its six biomes. The
method, its equations, the outputs and the checks are in [`METHODS.md`](METHODS.md).

## Pipeline

```
MapBiomas Collection 10 (Earth Engine asset, 40 bands)
   │  statistics/mapbiomas_brazil_annual_events_to_asset.py     8 Earth Engine tasks
   ▼  one image per class: base trajectory 1985-2024 + 39 annual loss/gain bands
   │  statistics/mapbiomas_brazil_export_statistics_time_intensity.py   16 tasks
   ▼  area of each event, by base trajectory, crossed with the territories
GeoJSON in Cloud Storage  ──download──▶  data/JSON/
   │  notebooks/scripts/mapbiomas_brazil_time_intensity_tables.py
   ▼  data/TABLES/*.xlsx
   │  notebooks/scripts/mapbiomas_brazil_time_intensity_figures.py
   ▼  data/FIGURES/**.png + captions.txt
```

The two Earth Engine steps run from a shell, not from the Code Editor. Everything after the
download is local and takes under a minute.

```
analysis/
├── statistics/          Earth Engine side (Python earthengine-api)
│   ├── config.py                 every constant: years, class remap, interval grids, assets
│   ├── annual_events.py          base trajectory and the 39 annual event bands
│   ├── trajectories_stats.py     grouped area reducers and the GCS export helper
│   ├── trajectory_legend.py      code book: the 8 trajectories and the 10 composites
│   ├── ee_init.py                ee.Initialize, reading the project from EE_PROJECT
│   └── mapbiomas_brazil_*.py     the two entry points
├── notebooks/scripts/   local side (pandas, matplotlib, xlsxwriter)
│   ├── tables.py, time_intensity.py   GeoJSON -> tidy table, unified size, components
│   ├── plots.py                       the figures
│   ├── mapbiomas_brazil_time_intensity_{tables,figures}.py   the two entry points
│   └── selftest_*.py                  checks that need no Earth Engine
├── images/mapbiomas_brazil_annual_events_to_asset.js   Code Editor twin of annual_events.py
└── data/                downloaded GeoJSON and locally built outputs (git-ignored)
```

## Reproducing

### 1. Check the code without Earth Engine

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements-tables.txt   # Python 3.12
python3 notebooks/scripts/selftest_time_intensity.py   # stdlib only
cd notebooks/scripts && ../../.venv/bin/python selftest_pipeline.py
```

The first proves by enumeration that exactly ten (event, trajectory) composites can occur,
checks that the interval grids tile the 39 annual transitions, and fails if the Code Editor
twin drifts from `config.py`. The second drives synthetic data through the real loading,
aggregation and plotting code and asserts that the area of the drawn bars equals the total
change.

### 2. Compute the statistics (needs Earth Engine and Cloud Storage)

```bash
pip install -r requirements-gee.txt
earthengine authenticate
```

Before running, set the three destinations in `statistics/config.py` that are marked
`PLACEHOLDER`: `ASSET_ANNUAL_EVENTS`, `GCS_BUCKET` and, if you use the Code Editor twin,
`assetOutput` in the `.js` file. Then, from `statistics/`:

```bash
export EE_PROJECT=<your-cloud-project>
python mapbiomas_brazil_annual_events_to_asset.py --dry-run     # builds the graph, queues nothing
python mapbiomas_brazil_annual_events_to_asset.py               # 8 tasks, 1h20-2h45 each
python mapbiomas_brazil_export_statistics_time_intensity.py     # 16 tasks, 20-30 min each
```

Download the resulting GeoJSON files into `data/JSON/<THEME>/<THEME>-<version>/`, which is
the layout the table script globs (see `PATH` in
`notebooks/scripts/mapbiomas_brazil_time_intensity_tables.py`).

### 3. Build the tables and figures

```bash
cd notebooks/scripts
../../.venv/bin/python mapbiomas_brazil_time_intensity_tables.py     # -> data/TABLES
../../.venv/bin/python mapbiomas_brazil_time_intensity_figures.py    # -> data/FIGURES
```

The figures are set in Palatino 10 pt; on systems without it matplotlib falls back to a
generic serif and the line breaks may differ slightly.

## Inputs

| asset | purpose |
|---|---|
| `projects/mapbiomas-public/assets/brazil/lulc/collection10/mapbiomas_brazil_collection10_coverage_v2` | land cover maps, 1985–2024 |
| `projects/mapbiomas-workspace/AUXILIAR/ESTATISTICAS/COLECAO8/VERSAO-1` | territory rasters (`country`, `refined_biome`) |
| `projects/mapbiomas-public/assets/papers/fonseca_et_all_2026/lulc_trajectories_per_class_col10` | published trajectories, used only as an optional cross-check |

## Decisions that matter when reading the numbers

- **The trajectory belongs to the whole 1985–2024 extent.** The interval says *when* a gain
  or loss happened; the trajectory says what that pixel did across the series.
- **The class definition is the paper's flat remap** (`config.CLASS_REMAP`, 49 classes into
  about 30), not the MapBiomas level 1–4 hierarchy, so that events and trajectory share one
  definition of presence and match the published asset.
- **The numbers count transitions, not area of land.** A pixel that flips twice in an
  interval counts twice; hence the column name `gross change (hectare)`. For area, use the
  `Quantity` component.
- **Interval grids tile the series.** `config.INTERVAL_GRIDS` has a 5-year and a 10-year
  grid; both cover exactly 39 transitions, with a deliberately shorter last interval.

See [`METHODS.md`](METHODS.md) for the reasoning and the evidence behind each.

## Reference

Bilintoh, T. M., Pontius, R. G., & Zhang, A. (2024). Methods to compare sites concerning a
category's change during various time intervals. *GIScience & Remote Sensing, 61*(1).
<https://doi.org/10.1080/15481603.2024.2409484>
