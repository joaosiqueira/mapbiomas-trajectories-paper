"""Configuration for the time-intensity pipeline (Collection 10, 1985-2024).

Edit the three PLACEHOLDER values below before running anything that writes to Earth
Engine or Cloud Storage: they are destinations that only you can write to.
"""

# Territory layers used to cross the events (country and biome rasters).
# Input only; read access is enough.
ASSET_THEMES = "projects/mapbiomas-workspace/AUXILIAR/ESTATISTICAS/COLECAO8/VERSAO-1"

# Version of the GeoJSON files written to Cloud Storage
OUTPUT_VERSION = '1'

COLLECTION = '10.0'

# PLACEHOLDER: a Cloud Storage bucket you can write to
GCS_BUCKET = 'YOUR-GCS-BUCKET'

# `{}` placeholders are the theme folder and OUTPUT_VERSION
GCS_OUTPUT_PATH_TEMPLATE = 'trajectories/time-intensity/{}/{}-{}'


# ---------------------------------------------------------------------------
# Time-intensity figures (Bilintoh, Pontius & Zhang 2024)
#
# ---------------------------------------------------------------------------

# PLACEHOLDER: an Earth Engine folder you can write to. Written by
# statistics/mapbiomas_brazil_annual_events_to_asset.py and
# images/mapbiomas_brazil_annual_events_to_asset.js (assetOutput there must match).
ASSET_ANNUAL_EVENTS = "projects/YOUR-PROJECT/assets/trajectories-c10/annual_events"

ANNUAL_EVENTS_VERSION = '1'

# Base trajectory published with Fonseca et al. (2026). Used only when
# USE_PUBLISHED_BASE is on, as a cross-check against our own base band.
ASSET_PUBLISHED_TRAJECTORIES = (
    "projects/mapbiomas-public/assets/papers/fonseca_et_all_2026/"
    "lulc_trajectories_per_class_col10")

# class_name -> band name in the published asset.
# The published bands are abbreviated with a traj_ prefix; the paper script's in-memory
# names (forest, pasture, ...) are NOT what got written. Read off the asset itself.
PUBLISHED_BAND_BY_CLASS = {
    'forest_formation': 'traj_for',
    'pasture': 'traj_pas',
    'savanna_formation': 'traj_sav',
    'grassland': 'traj_gra',
    'river_lake_and_ocean': 'traj_wat',
    'urban_area': 'traj_urb',
    'agriculture': 'traj_agr',
    'wetland': 'traj_wet',
}

# The collection 10 LULC stack the whole pipeline reads
ASSET_LULC = ('projects/mapbiomas-public/assets/brazil/lulc/collection10/'
              'mapbiomas_brazil_collection10_coverage_v2')

BASE_TRAJECTORY_BAND = 'trajectories_1985_2024'

YEARS = list(range(1985, 2025))

FULL_EXTENT = (1985, 2024)

N_TRANSITIONS = len(YEARS) - 1  # 39

# The 8 classes the figures are drawn for, as (level_id, class_id, class_name)
INTENSITY_CLASS_IDS = [
    (2, 3, 'forest_formation'),
    (2, 4, 'savanna_formation'),
    (2, 11, 'wetland'),
    (2, 12, 'grassland'),
    (2, 15, 'pasture'),
    (2, 18, 'agriculture'),
    (2, 24, 'urban_area'),
    (2, 33, 'river_lake_and_ocean'),
]

INTENSITY_THEMES = [
    ("country", "raster"),
    ("refined_biome", "raster"),
]

# Contiguous, non-overlapping tilings of the 39 annual transitions. The last interval of
# each grid is deliberately shorter (4 and 9 years); bar width shows it in the figure.
# These must not overlap - the area of each bar is meant to sum to
# the total change. notebooks/scripts/selftest_time_intensity.py checks the tiling.
INTERVAL_GRIDS = {
    '5y': [(1985, 1990), (1990, 1995), (1995, 2000), (2000, 2005),
           (2005, 2010), (2010, 2015), (2015, 2020), (2020, 2024)],
    '10y': [(1985, 1995), (1995, 2005), (2005, 2015), (2015, 2024)],
}


# Feature ids of the territory rasters, with the names MapBiomas publishes in English.
# Taken from the ids in the theme assets, but not from their NAME field: that column is
# Portuguese despite its name, identical to NAME_PT_BR.
TERRITORY_NAMES = {
    'country': {1: 'Brazil'},
    'refined_biome': {
        2: 'Amazon',
        3: 'Caatinga',
        4: 'Cerrado',
        5: 'Atlantic Forest',
        6: 'Pampa',
        7: 'Pantanal',
    },
}

def territoryName(category, feature_id):
    """Readable name for a (category, feature_id) pair, falling back to the raw ids."""

    try:
        return TERRITORY_NAMES[category][int(feature_id)]
    except (KeyError, TypeError, ValueError):
        return '{} {}'.format(category, feature_id)


# Class definition used by the time-intensity pipeline: the explicit remap from the
# companion paper repository, folding the 49 collection 10 classes into ~30. It is what
# produced the published trajectory asset, so using it keeps these figures comparable
# with Fonseca et al. (2026). Note this is NOT the level 1-4 legend hierarchy used by
# the other collection 10 products.
CLASS_REMAP = {
    # Forest formation
    1: 1, 3: 3,
    # Savanna formation
    4: 4,
    # Merged into forest formation
    5: 3, 6: 3, 49: 3,
    # Mangrove
    45: 45,
    # Forest plantation
    9: 9,
    # Natural non-forest formations
    10: 10, 11: 11, 12: 12, 32: 32, 29: 29, 50: 50,
    13: 13, 42: 42, 43: 43, 44: 44, 66: 66,
    # Grassland receives 63
    63: 12,
    # Pasture
    14: 14, 15: 15,
    # Agriculture absorbs every crop subtype
    18: 18, 19: 18, 39: 18, 20: 18, 40: 18, 62: 18, 41: 18,
    57: 18, 58: 18, 36: 18, 46: 18, 47: 18, 35: 18, 65: 18, 48: 18,
    # Mosaic, non-vegetated, urban, mining
    21: 21, 22: 22, 23: 23, 24: 24, 30: 30, 25: 25, 61: 61, 26: 26,
    # Water bodies and aquaculture
    33: 33, 31: 31, 34: 34, 75: 75,
}
