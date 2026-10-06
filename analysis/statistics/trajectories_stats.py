"""Shared helpers for the Collection 10 trajectory area statistics.

In collections 6 and 8 these functions were copy-pasted into every
`mapbiomas_brazil_export_statistics_*.py`, which is how those scripts drifted apart.
Here they live in one place and each export script only declares its configuration.

Every function is server-side Earth Engine; nothing is fetched to the client.
"""
import ee

def pixelArea():
    """Pixel area in km2.

    A function, not a module-level constant: an ee call at import time runs before the
    caller has had a chance to call ee.Initialize(), and fails with
    "Earth Engine client library not initialized".
    """

    return ee.Image.pixelArea().divide(1000000)


def getProperties(item):
    """Turns one grouped-reducer entry into a Feature with a [class, area] data list."""

    item = ee.Dictionary(item)

    year = ee.Dictionary(ee.List(item.get('groups')).get(0)).get('ANO')

    feature = ee.Feature(None) \
        .set('featureid', ee.String(item.get('featureid'))) \
        .set("year", year) \
        .set("data", [])

    areasLis = ee.List(ee.Dictionary(
        ee.List(item.get('groups')).get(0)).get('groups'))

    def temp(obj, feature):
        obj = ee.Dictionary(obj)

        classe = ee.String(ee.Number(obj.get('CLASSE')).toUint32())

        area = obj.get('sum')

        datalist = ee.List(ee.Feature(feature).get(
            'data')).add([classe, area])

        return ee.Feature(feature).set('data', datalist)

    feature = areasLis.iterate(
        temp, feature
    )

    return feature


def calculateArea(image, regions, geometry, year1, year2):
    """Grouped zonal sum of pixel area by featureid x period x class.

    The period is encoded as a single number, `year1 * 10000 + year2`, and the table
    scripts under notebooks/scripts decode it back. Changing this breaks them.
    """

    reducer = ee.Reducer.sum().group(1, 'CLASSE').group(1, 'ANO').group(1, 'featureid')

    areas = pixelArea().addBands(regions).addBands(ee.Image((year1 * 10000) + year2)).addBands(image) \
        .reduceRegion(
            reducer=reducer,
            geometry=geometry,
            scale=30,
            maxPixels=1e12
    )

    collection = ee.FeatureCollection(
        ee.List(areas.get('groups'))
        .map(getProperties)
    )

    return collection


def calculateAreaUsingRaster(image, theme, year1, year2):
    """Crosses the product with a painted feature-id raster covering the whole theme."""

    geometry = theme.geometry().bounds()

    areas = calculateArea(
        image,
        theme,
        geometry,
        year1=year1,
        year2=year2
    )

    return ee.FeatureCollection(areas)


def calculateAreaUsingVector(image, theme, year1, year2, propColor):
    """Crosses the product with a FeatureCollection, one reduceRegion per feature."""

    areas = theme.map(
        lambda feature:
            calculateArea(
                image,
                ee.Image().int64().paint(
                    featureCollection=ee.FeatureCollection(feature),
                    color=propColor),
                feature.geometry(),
                year1=year1,
                year2=year2
            )
    )

    return ee.FeatureCollection(areas).flatten()


def calculateAreaByTheme(image, themeName, themeType, assetThemes, year1, year2,
                         propColor='FEATURE_ID'):
    """Dispatches to the raster or vector path according to the theme type."""

    if themeType == 'raster':
        theme = ee.Image('{}/{}-{}'.format(assetThemes, themeName, themeType))

        return calculateAreaUsingRaster(
            image=image,
            theme=theme,
            year1=year1,
            year2=year2)

    theme = ee.FeatureCollection('{}/{}'.format(assetThemes, themeName))

    return calculateAreaUsingVector(
        image=image,
        theme=theme,
        year1=year1,
        year2=year2,
        propColor=propColor)


def export(areas, name, bucket, gcsPath):
    """Queues a GeoJSON export of the area table to Cloud Storage."""

    task = ee.batch.Export.table.toCloudStorage(
        collection=areas,
        bucket=bucket,
        fileNamePrefix=gcsPath + '/' + name,
        description=name[0:99],
        fileFormat="GeoJSON"
    )

    task.start()


def calculateWeightedArea(weightedArea, classImage, regions, geometry, year1, year2):
    """Like calculateArea, but sums an already weighted area image.

    The time-intensity statistics need `pixel area x number of events in the interval`,
    not plain pixel area, because a pixel that flips twice inside an interval must count
    twice. `weightedArea` carries that product; `classImage` carries the group key.

    Both must already be masked to the pixels that actually changed - see
    maskedEventArea. The reducer chain is the same as calculateArea's on purpose.
    """

    reducer = ee.Reducer.sum().group(1, 'CLASSE').group(1, 'ANO').group(1, 'featureid')

    areas = weightedArea.addBands(regions).addBands(ee.Image((year1 * 10000) + year2)).addBands(classImage) \
        .reduceRegion(
            reducer=reducer,
            geometry=geometry,
            scale=30,
            maxPixels=1e12
    )

    collection = ee.FeatureCollection(
        ee.List(areas.get('groups'))
        .map(getProperties)
    )

    return collection


def maskedEventArea(eventImage, baseImage, bandNames, eventValue, compositeOffset):
    """Builds the (weighted area, composite key) pair for one interval and one direction.

    `eventImage` holds one band per annual transition with 0/1/2; `bandNames` selects the
    transitions inside the interval; `eventValue` is 1 for loss or 2 for gain.

    Counting first and weighting once replaces one reduceRegion per year with one per
    interval, and is arithmetically the same as summing the per-year areas.

    BOTH returned images are masked to count > 0. Masking only the value band would make
    every unchanged pixel in the territory emit a group with sum 0, including composites
    that cannot occur (17, 18, 27, 28), which would blow up the group count and break the
    ten-composite invariant the downstream checks rely on.
    """

    count = eventImage.select(bandNames).eq(eventValue).reduce(ee.Reducer.sum())

    mask = count.gt(0)

    weightedArea = pixelArea().multiply(count).updateMask(mask)

    composite = baseImage.add(compositeOffset).updateMask(mask)

    return weightedArea, composite


def calculateWeightedAreaByTheme(weightedArea, classImage, themeName, themeType,
                                 assetThemes, year1, year2, propColor='FEATURE_ID'):
    """calculateAreaByTheme for the weighted case."""

    if themeType == 'raster':
        theme = ee.Image('{}/{}-{}'.format(assetThemes, themeName, themeType))

        return calculateWeightedArea(
            weightedArea, classImage, theme, theme.geometry().bounds(), year1, year2)

    theme = ee.FeatureCollection('{}/{}'.format(assetThemes, themeName))

    areas = theme.map(
        lambda feature:
            calculateWeightedArea(
                weightedArea,
                classImage,
                ee.Image().int64().paint(
                    featureCollection=ee.FeatureCollection(feature),
                    color=propColor),
                feature.geometry(),
                year1,
                year2)
    )

    return ee.FeatureCollection(areas).flatten()
