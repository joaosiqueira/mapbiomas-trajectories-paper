/**
 * Code Editor twin of statistics/mapbiomas_brazil_annual_events_to_asset.py.
 *
 * The Python version is what the pipeline runs, and it is the one verified against the
 * published paper asset (100.0000% pixel agreement at native 30 m). This file exists for
 * what Python cannot do: put the result on a map and look at it.
 *
 * The two therefore hold the same years, class list, 49-class remap and trajectory
 * rules. That duplication is deliberate but checked, not trusted:
 * notebooks/scripts/selftest_time_intensity.py parses this file and fails if it drifts
 * away from statistics/config.py. Edit one side, run the selftest, fix the other.
 *
 * MapBiomas Brazil - annual change events + base trajectory (Collection 10, 1985-2024).
 *
 * Feeds the time-intensity figures (Bilintoh, Pontius & Zhang 2024). For each of the 8
 * classes of interest it exports ONE byte image with 40 bands:
 *
 *   trajectories_1985_2024   the base trajectory 1-8 over the whole extent
 *   event_1985_1986 ... event_2023_2024   (39 bands)
 *                            0 = no change, 1 = the class was lost, 2 = it was gained
 *
 * The 39 annual transitions are stored as separate bands, one asset per class, so the
 * statistics step can aggregate them into any interval grid without recomputing.
 *
 * Why the base trajectory is recomputed here rather than read from the existing
 * trajectories/ assets: the events and the base MUST use the same definition of
 * "presence". Computing both from one presence stack makes that true by construction
 * instead of by coincidence.
 *
 * Runs in the GEE Code Editor only.
 */

// Collection 10 public asset: a single multi-band Image (one band per year).
var asset = 'projects/mapbiomas-public/assets/brazil/lulc/collection10/mapbiomas_brazil_collection10_coverage_v2';

// Output asset folder
var assetOutput = 'projects/YOUR-PROJECT/assets/trajectories-c10/annual_events';

// Output version
var version = '1';

var years = [
    1985, 1986, 1987, 1988, 1989, 1990, 1991, 1992, 1993, 1994,
    1995, 1996, 1997, 1998, 1999, 2000, 2001, 2002, 2003, 2004,
    2005, 2006, 2007, 2008, 2009, 2010, 2011, 2012, 2013, 2014,
    2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024
];

/**
 * Class definition.
 *
 * This is the explicit remap of ../trajectories.js (the dashboard), NOT the level 1-4
 * legend hierarchy of the MapBiomas modules. It is what produced the
 * published asset
 * projects/mapbiomas-public/assets/papers/fonseca_et_all_2026/lulc_trajectories_per_class_col10,
 * so using it here keeps these figures comparable with Fonseca et al. (2026).
 *
 * The practical differences: 5, 6 and 49 are folded into forest formation (3), 63 into
 * grassland (12), and every crop subtype into agriculture (18).
 */
var classRemap = {
    // Forest formation
    1: 1, 3: 3,
    // Savanna formation
    4: 4,
    // Merged into Forest (3)
    5: 3, 6: 3, 49: 3,
    // Mangrove
    45: 45,
    // Forest plantation
    9: 9,
    // Natural non-forest formations
    10: 10, 11: 11, 12: 12, 32: 32, 29: 29, 50: 50, 13: 13, 42: 42, 43: 43, 44: 44, 66: 66,
    // Grassland (12) receives 63
    63: 12,
    // Pasture
    14: 14, 15: 15,
    // Agriculture (18) absorbs all crop subtypes
    18: 18, 19: 18, 39: 18, 20: 18, 40: 18, 62: 18, 41: 18,
    57: 18, 58: 18, 36: 18, 46: 18, 47: 18, 35: 18, 65: 18, 48: 18,
    // Mosaic, non-vegetated, urban, mining
    21: 21, 22: 22, 23: 23, 24: 24, 30: 30, 25: 25, 61: 61, 26: 26,
    // Water bodies and aquaculture
    33: 33, 31: 31, 34: 34, 75: 75
};

// The 8 classes the time-intensity figures are drawn for
var classList = [
    { 'class_name': 'forest_formation', 'class_id': 3 },
    { 'class_name': 'savanna_formation', 'class_id': 4 },
    { 'class_name': 'wetland', 'class_id': 11 },
    { 'class_name': 'grassland', 'class_id': 12 },
    { 'class_name': 'pasture', 'class_id': 15 },
    { 'class_name': 'agriculture', 'class_id': 18 },
    { 'class_name': 'urban_area', 'class_id': 24 },
    { 'class_name': 'river_lake_and_ocean', 'class_id': 33 }
];

// Define a bbox to export region
var region = ee.Geometry.Polygon(
    [
        [
            [-74.34415028048886, 6.041474308055545],
            [-74.34415028048886, -34.38941142226404],
            [-34.17813465548886, -34.38941142226404],
            [-34.17813465548886, 6.041474308055545]
        ]
    ], null, false
);

var classFrom = Object.keys(classRemap).map(function (key) { return Number(key); });
var classTo = Object.keys(classRemap).map(function (key) { return classRemap[key]; });

var bands = years.map(
    function (year) {
        return 'classification_' + year.toString();
    }
);

// LULC stack with the paper's class definition applied
var lulc = ee.Image(ee.List(bands).iterate(
    function (band, result) {
        band = ee.String(band);

        var remapped = ee.Image(asset).select([band])
            .remap(classFrom, classTo)
            .rename([band]);

        return ee.Image(result).addBands(remapped);
    },
    ee.Image().select()
));

print('lulc remapped', lulc);

/**
 * Binary presence stack for one class: 1 where the class is present, 0 otherwise.
 * @param {number} classId
 * @returns {ee.Image} one band per year, named as the classification bands
 */
var presenceStack = function (classId) {

    return ee.Image(ee.List(bands).iterate(
        function (band, result) {
            band = ee.String(band);

            var present = lulc.select([band]).eq(classId).rename([band]);

            return ee.Image(result).addBands(present);
        },
        ee.Image().select()
    ));
};

/**
 * The 1-8 base trajectory over the whole extent.
 * Same rules, same order, as the trajectory classification in ../trajectories.js.
 * @param {ee.Image} presence
 * @returns {ee.Image} single band `trajectories_1985_2024`
 */
var baseTrajectory = function (presence) {

    var nChanges = presence.reduce(ee.Reducer.countRuns()).subtract(1);

    var nChangesEq0 = nChanges.eq(0);
    var nChangesEq1 = nChanges.eq(1);
    var nChangesGt1 = nChanges.gt(1);

    var t1 = presence.select([bands[0]]);
    var tn = presence.select([bands[bands.length - 1]]);

    var abAbCh0 = t1.eq(0).and(nChangesEq0);
    var prPrCh0 = t1.eq(1).and(nChangesEq0);
    var abPrCh1 = t1.eq(0).and(nChangesEq1).and(tn.eq(1));
    var prAbCh1 = t1.eq(1).and(nChangesEq1).and(tn.eq(0));
    var abPrCh2 = t1.eq(0).and(nChangesGt1).and(tn.eq(1));
    var prAbCh2 = t1.eq(1).and(nChangesGt1).and(tn.eq(0));
    var abAbCh1 = t1.eq(0).and(nChangesGt1).and(tn.eq(0));
    var prPrCh1 = t1.eq(1).and(nChangesGt1).and(tn.eq(1));

    return ee.Image(0)
        .where(prAbCh1, 1)  // [1] Presence->Loss->Absence
        .where(abPrCh1, 2)  // [2] Absence->Gain->Presence
        .where(prAbCh2, 3)  // [3] Presence->Alternation->Loss->Absence
        .where(abPrCh2, 4)  // [4] Absence->Alternation->Gain->Presence
        .where(prPrCh1, 5)  // [5] Presence->Alternation->Presence
        .where(abAbCh1, 6)  // [6] Absence->Alternation->Absence
        .where(prPrCh0, 7)  // [7] Presence->Stable->Presence
        .where(abAbCh0, 8)  // [8] Absence->Stable->Absence
        .rename(['trajectories_1985_2024']);
};

/**
 * One band per annual transition: 0 no change, 1 loss, 2 gain.
 * Left UNMASKED on purpose: the statistics step masks on the interval count, and a
 * masked 0 here would fight that.
 * @param {ee.Image} presence
 * @returns {ee.Image} 39 bands
 */
var annualEvents = function (presence) {

    var events = [];

    for (var i = 0; i < years.length - 1; i++) {
        var previous = presence.select([bands[i]]);
        var current = presence.select([bands[i + 1]]);

        var loss = previous.eq(1).and(current.eq(0));
        var gain = previous.eq(0).and(current.eq(1));

        var bandName = 'event_' + years[i].toString() + '_' + years[i + 1].toString();

        events.push(
            ee.Image(0)
                .where(loss, 1)
                .where(gain, 2)
                .rename([bandName])
        );
    }

    return ee.Image.cat(events);
};

var visParams = {
    'trajectories': {
        'min': 0,
        'max': 8,
        'palette': [
            "#ffffff", //[0] Mask
            "#941004", //[1] Presence->Loss->Absence
            "#020e7a", //[2] Absence->Gain->Presence
            "#f5261b", //[3] Presence->Alternation->Loss->Absence
            "#14a5e3", //[4] Absence->Alternation->Gain->Presence
            "#8b8000", //[5] Presence->Alternation->Presence
            "#ffff00", //[6] Absence->Alternation->Absence
            "#666666", //[7] Presence->Stable->Presence
            "#cfcfcf", //[8] Absence->Stable->Absence
        ],
        'format': 'png'
    },
    'event': {
        'min': 0,
        'max': 2,
        'palette': ["#ffffff", "#941004", "#020e7a"],
        'format': 'png'
    }
};

classList.forEach(
    function (obj) {

        var presence = presenceStack(obj.class_id);

        var trajectories = baseTrajectory(presence);
        var events = annualEvents(presence);

        var image = trajectories.addBands(events)
            .byte()
            .set('class_id', obj.class_id)
            .set('class_name', obj.class_name)
            .set('collection', '10.0')
            .set('version', version)
            .set('years', years.join(','));

        Map.addLayer(image.select(['trajectories_1985_2024']).selfMask(),
            visParams.trajectories,
            'trajectories_1985_2024_' + obj.class_name,
            false
        );

        Map.addLayer(image.select(['event_2023_2024']).selfMask(),
            visParams.event,
            'event_2023_2024_' + obj.class_name,
            false
        );

        var assetName = 'annual_events_' + obj.class_name + '_v' + version;

        Export.image.toAsset({
            'image': image,
            'description': assetName,
            'assetId': assetOutput + '/' + assetName,
            'pyramidingPolicy': { '.default': 'mode' },
            'region': region,
            'scale': 30,
            'maxPixels': 1e13,
        });
    }
);

print('classes to export', classList.length, '- bands per image', years.length);
