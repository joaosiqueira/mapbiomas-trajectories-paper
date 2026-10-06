"""Builds the annual change events and the base trajectory for one class.

This is the Python implementation. images/mapbiomas_brazil_annual_events_to_asset.js is
its Code Editor twin, kept for what Python cannot do (Map.addLayer). The years, the class
list, the 49-class remap and the trajectory rules exist in both, so
notebooks/scripts/selftest_time_intensity.py parses the JS and fails if either drifts
away from config.py.

Presence is defined by config.CLASS_REMAP, the paper's flat remap. The events and the
base trajectory are computed from one presence stack, so they cannot disagree about what
"present" means.
"""
import ee

import config


def remapLists():
    """CLASS_REMAP as the two parallel lists ee.Image.remap wants."""

    source = sorted(config.CLASS_REMAP)

    return source, [config.CLASS_REMAP[key] for key in source]


def classificationBands(years=None):
    """Band names of the LULC stack, in year order."""

    return ['classification_{}'.format(year) for year in (years or config.YEARS)]


def eventBandNames(year1, year2):
    """Event band names for the transitions inside [year1, year2]."""

    return ['event_{}_{}'.format(year, year + 1) for year in range(year1, year2)]


def remappedLulc():
    """The collection 10 stack with the paper's class definition applied."""

    source, target = remapLists()

    asset = ee.Image(config.ASSET_LULC)

    bands = classificationBands()

    def addBand(band, result):
        band = ee.String(band)

        remapped = asset.select([band]).remap(source, target).rename([band])

        return ee.Image(result).addBands(remapped)

    return ee.Image(ee.List(bands).iterate(addBand, ee.Image().select()))


def presenceStack(lulc, class_id):
    """Binary presence: 1 where the class is present that year, 0 otherwise."""

    bands = classificationBands()

    def addBand(band, result):
        band = ee.String(band)

        return ee.Image(result).addBands(
            lulc.select([band]).eq(class_id).rename([band]))

    return ee.Image(ee.List(bands).iterate(addBand, ee.Image().select()))


def baseTrajectory(presence):
    """The 1-8 trajectory over the whole extent.

    Same rules and same order as the trajectory classification in trajectories.js; later
    .where() calls win.
    notebooks/scripts/selftest_time_intensity.py holds a pure-Python twin of these rules
    and proves they classify every possible presence series.
    """

    bands = classificationBands()

    nChanges = presence.reduce(ee.Reducer.countRuns()).subtract(1)

    eq0 = nChanges.eq(0)
    eq1 = nChanges.eq(1)
    gt1 = nChanges.gt(1)

    t1 = presence.select([bands[0]])
    tn = presence.select([bands[-1]])

    return (ee.Image(0)
            .where(t1.eq(1).And(eq1).And(tn.eq(0)), 1)
            .where(t1.eq(0).And(eq1).And(tn.eq(1)), 2)
            .where(t1.eq(1).And(gt1).And(tn.eq(0)), 3)
            .where(t1.eq(0).And(gt1).And(tn.eq(1)), 4)
            .where(t1.eq(1).And(gt1).And(tn.eq(1)), 5)
            .where(t1.eq(0).And(gt1).And(tn.eq(0)), 6)
            .where(t1.eq(1).And(eq0), 7)
            .where(t1.eq(0).And(eq0), 8)
            .rename([config.BASE_TRAJECTORY_BAND]))


def annualEvents(presence):
    """One band per annual transition: 0 no change, 1 loss, 2 gain.

    Left unmasked on purpose - the statistics step masks on the per-interval count, and
    a masked zero here would fight that.
    """

    bands = classificationBands()

    images = []

    for index in range(len(config.YEARS) - 1):
        previous = presence.select([bands[index]])
        current = presence.select([bands[index + 1]])

        name = 'event_{}_{}'.format(config.YEARS[index], config.YEARS[index + 1])

        images.append(
            ee.Image(0)
            .where(previous.eq(1).And(current.eq(0)), 1)
            .where(previous.eq(0).And(current.eq(1)), 2)
            .rename([name])
        )

    return ee.Image.cat(images)


def buildClassImage(class_id, class_name, lulc=None):
    """The 40-band image for one class: base trajectory plus 39 event bands."""

    lulc = remappedLulc() if lulc is None else lulc

    presence = presenceStack(lulc, class_id)

    image = baseTrajectory(presence).addBands(annualEvents(presence))

    return (image.byte()
            .set('class_id', class_id)
            .set('class_name', class_name)
            .set('collection', config.COLLECTION)
            .set('version', config.ANNUAL_EVENTS_VERSION))


def assetId(class_name):
    """Where buildClassImage is stored for a class."""

    return '{}/annual_events_{}_v{}'.format(
        config.ASSET_ANNUAL_EVENTS, class_name, config.ANNUAL_EVENTS_VERSION)


def loadAnnualEvents(class_id, class_name, usePrecomputed=True, usePublishedBase=False,
                     lulc=None):
    """Returns (base trajectory, event bands) for one class.

    With `usePrecomputed` the stored asset is read; otherwise everything is rebuilt in
    the same graph, which needs no asset at all and is the quick way to try a single
    territory. `usePublishedBase` swaps in the trajectory published with the paper - a
    way to check the two agree, since a disagreement shows up as impossible composites.
    """

    if usePrecomputed:
        image = ee.Image(assetId(class_name))
    else:
        image = buildClassImage(class_id, class_name, lulc=lulc)

    events = image.select(eventBandNames(*config.FULL_EXTENT))

    if usePublishedBase:
        base = ee.Image(config.ASSET_PUBLISHED_TRAJECTORIES) \
            .select([config.PUBLISHED_BAND_BY_CLASS[class_name]])
    else:
        base = image.select([config.BASE_TRAJECTORY_BAND])

    return base, events
