"""Area of annual gain/loss events crossed with the full-extent trajectory.

Feeds the time-intensity figures. For every class and territory it exports one GeoJSON
holding, for each interval of each grid, the gross changed area broken down by the
pixel's 1985-2024 trajectory - plus the unified-size rows that are the denominator.

Uses the encoding `annual_event * 10 + base_trajectory`, so a
CLASSE value of 13 reads "area lost during this interval, on pixels whose long-run
trajectory is Presence->Alternation->Loss->Absence".

Rows are told apart by their CLASSE value:
    1..8    unified-size rows  (grid property == 'base')
    11..16  loss rows
    22..26  gain rows

Run: python mapbiomas_brazil_export_statistics_time_intensity.py
"""
import ee

import annual_events
import config
import ee_init
import trajectory_legend as legend
from trajectories_stats import (calculateAreaByTheme, calculateWeightedAreaByTheme,
                                maskedEventArea, export)

# reads the Cloud project from EE_PROJECT (see ee_init.py)
ee_init.initialize()

PRODUCT = 'INTENSIDADE-TEMPO'

FILE_LABEL = 'time.intensity'

# Read the base trajectory from the published paper asset instead of the band computed
# by mapbiomas_brazil_annual_events_to_asset.js. Off by default: our own band is
# guaranteed to share its presence definition with the events. Turning it on is a way to
# check the two agree - if they disagree, impossible composites (17, 18, 27, 28) appear
# and the table step rejects them.
USE_PUBLISHED_BASE = False

# One task per (class, theme) = 16. Add 'grid' or 'interval' if a task times out.
BATCH_BY = ('class', 'theme')

# Read the stored annual_events asset. Set to False to rebuild the events inside this
# same graph instead, which needs no asset at all - handy to try one territory quickly,
# and the only option before mapbiomas_brazil_annual_events_to_asset.py has been run.
USE_PRECOMPUTED_ASSET = True

eventBandNames = annual_events.eventBandNames


def intervalCollections(base, events, themeName, themeType):
    """One FeatureCollection per interval per direction, for every grid."""

    parts = []

    for gridName, intervals in config.INTERVAL_GRIDS.items():

        for year1, year2 in intervals:

            bandNames = eventBandNames(year1, year2)

            for eventValue, offset in ((legend.LOSS, 10), (legend.GAIN, 20)):

                weightedArea, composite = maskedEventArea(
                    eventImage=events,
                    baseImage=base,
                    bandNames=bandNames,
                    eventValue=eventValue,
                    compositeOffset=offset)

                areas = calculateWeightedAreaByTheme(
                    weightedArea=weightedArea,
                    classImage=composite,
                    themeName=themeName,
                    themeType=themeType,
                    assetThemes=config.ASSET_THEMES,
                    year1=year1,
                    year2=year2)

                parts.append(areas.map(lambda feature: feature.set('grid', gridName)))

    return parts


def unifiedSizeCollection(base, themeName, themeType):
    """Plain area per base trajectory 1-8 over the whole extent: the denominator.

    Travels in the same file as the numerator on purpose. A denominator computed from a
    different asset or version silently yields wrong percentages.
    """

    areas = calculateAreaByTheme(
        image=base,
        themeName=themeName,
        themeType=themeType,
        assetThemes=config.ASSET_THEMES,
        year1=config.FULL_EXTENT[0],
        year2=config.FULL_EXTENT[1])

    return areas.map(lambda feature: feature.set('grid', 'base'))


for level_id, class_id, class_name in config.INTENSITY_CLASS_IDS:

    base, events = annual_events.loadAnnualEvents(
        class_id=class_id,
        class_name=class_name,
        usePrecomputed=USE_PRECOMPUTED_ASSET,
        usePublishedBase=USE_PUBLISHED_BASE)

    for themeName, themeType in config.INTENSITY_THEMES:

        parts = [unifiedSizeCollection(base, themeName, themeType)]
        parts.extend(intervalCollections(base, events, themeName, themeType))

        areas = ee.FeatureCollection(parts).flatten().map(
            lambda feature: feature
            .set('collection', config.COLLECTION)
            .set('category', themeName)
            .set('level_id', level_id)
            .set('class_id', class_id)
            .set('class_name', class_name)
            .set('version', config.ANNUAL_EVENTS_VERSION)
        )

        name = "collection-{}-{}-{}-{}.{}-{}-{}".format(
            config.COLLECTION, FILE_LABEL, themeName.replace('_', '.'),
            config.FULL_EXTENT[0], config.FULL_EXTENT[1],
            class_name.replace('_', '.'), config.OUTPUT_VERSION)

        print(name)

        export(areas, name, config.GCS_BUCKET,
               config.GCS_OUTPUT_PATH_TEMPLATE.format(
                   themeName.upper(), PRODUCT, config.OUTPUT_VERSION))

print('\n{} tasks queued'.format(
    len(config.INTENSITY_CLASS_IDS) * len(config.INTENSITY_THEMES)))
