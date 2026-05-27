
/**
 * @description
 *      Dashboard for LULC trajectories analysis
 *  
 * @author
 *      João Siqueira, Mapbiomas.
 *      Robert Gilmore Pontius Jr, Ph.D, Clark University.
 * 
 * @contact
 *      Julia Shimbo, Marcos Rosa and João Siqueira
 *      contato@mapbiomas.org
 *
 * @version
 *    1.0.0 - 
 */
/**
 * import modules 
 */

var Mapp = require('users/joaovsiqueira1/packages:Mapp.js');
var Legend = require('users/joaovsiqueira1/packages:Legend.js');
var Palettes = require('users/mapbiomas/modules:Palettes.js');
var ColorRamp = require('users/joaovsiqueira1/packages:ColorRamp.js');
/**
 * define parameters 
 */

var palettes = require('users/mapbiomas/modules:Palettes.js');
var vis = {'min': 0,'max': 62,'palette': palettes.get('classification8')}

// ---- External GEE assets ----
var estados = ee.FeatureCollection("projects/mapbiomas-workspace/AUXILIAR/estados-2017--");
var trajectoriesImage = ee.Image("projects/nexgenmap/MapBiomas_TOOLs/Trajectories/Trajs_image_col9");
var assetLulc = ee.Image('projects/mapbiomas-public/assets/brazil/lulc/collection10/mapbiomas_brazil_collection10_coverage_v2');
var assetTerritories = ee.ImageCollection('projects/mapbiomas-territories/assets/TERRITORIES/LULC/BRAZIL/COLLECTION9/dashboard')
    .filter(ee.Filter.eq('CATEG_ID', 4)).max();

print(assetLulc, "asset")

// Define the years to process
var anos = ['1985','1986','1987','1988','1989','1990','1991','1992','1993','1994','1995',
            '1996','1997','1998','1999','2000','2001','2002','2003','2004','2005','2006',
            '2007','2008','2009','2010','2011','2012','2013','2014','2015','2016','2017',
            '2018','2019','2020','2021','2022','2023','2024'];


// Stack remapped classification bands for all years using server-side iteration
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
var classFrom = Object.keys(classRemap).map(
    function(k) {
        return Number(k);
    });

var classTo = Object.keys(classRemap).map(
    function(k) {
        return classRemap[k];
    });

print(classFrom);
print(classTo);

var class_outTotal = ee.Image(ee.List(anos).iterate(
    function(year, result) {
        var bandName = ee.String('classification_').cat(ee.String(year));

        var classYear = assetLulc.select(bandName)
        .remap(classFrom, classTo)
        .rename(bandName);

    return ee.Image(result).addBands(classYear);
}, ee.Image()));

var assetLulc = class_outTotal

print(assetLulc);

var class_2024 = assetLulc.select('classification_2024')
var class_1985 = assetLulc.select('classification_1985')


Map.addLayer(class_2024.select('classification_2024'), vis, "classification2024", false)
Map.addLayer(class_1985.select('classification_1985'), vis, "classification1985", false)

// the analysis runs only for the groups below
var classIds = [
    [3],                                     // forest
    [15],                                    // pasture
    [11],
    [18],                                   // crops
    [33],
    [4],
    [12],
    [24],
];

var periods = [
    [1985, 2024],
];

var mpbPalette = Palettes.get('classification7');

// defined user functions
/**
 * 
 * @param {*} image 
 * @returns 
 */
var calculateNumberOfClasses = function (image) {

    var nClasses = image.reduce(ee.Reducer.countDistinctNonNull());

    return nClasses.rename('number_of_classes');
};

/**
 * 
 * @param {*} image 
 * @returns 
 */
var calculateNumberOfChanges = function (image) {

    var nChanges = image.reduce(ee.Reducer.countRuns()).subtract(1);

    return nChanges.rename('number_of_changes');
};

/**
 * 
 * @param {*} image 
 * @returns 
 */
var calculateNumberOfPresence = function (image) {

    var nChanges = image.reduce(ee.Reducer.sum());

    return nChanges.rename('number_of_presence');
};

/**
 * visualization
 */
var visParams = {
    'number_of_presence': {
        'min': 0,
        'max': 39,
        'palette': [
            "#ffffff",
            "#fff5f0",
            "#fee0d2",
            "#fcbba1",
            "#fc9272",
            "#fb6a4a",
            "#ef3b2c",
            "#cb181d",
            "#a50f15",
            "#67000d"
        ],
        'format': 'png'
    },
    'number_of_changes': {
        'min': 0,
        'max': 6,
        'palette': [
            "#ffffff",
            "#fee0d2",
            "#fcbba1",
            "#fb6a4a",
            "#ef3b2c",
            "#a50f15",
            "#67000d"
        ],
        'format': 'png'
    },
    'number_of_classes': {
        'min': 0,
        'max': 5,
        'palette': [
            "#ffffff",
            "#C8C8C8",
            "#AE78B2",
            "#772D8F",
            "#4C226A",
            "#22053A"
        ],
        'format': 'png'
    },
    'stable': {
        'min': 0,
        'max': 62,
        'palette': mpbPalette,
        'format': 'png'
    },
    'trajectories': {
        'min': 0,
        'max': 8,
        'palette': [
            "#ffffff", //[0] Mask 
            "#941004", //[1] Presence🡪Loss🡪Absence
            "#020e7a", //[2] Absence🡪Gain🡪Presence
            "#f5261b", //[3] Presence🡪Alternation🡪Loss🡪Absence
            "#14a5e3", //[4] Absence🡪Alternation🡪Gain🡪Presence
            "#8b8000", //[5] Presence🡪Alternation🡪Presence
            "#ffff00", //[6] Absence🡪Alternation🡪Absence
            "#666666", //[7] Presence🡪Stable🡪Presence
            "#cfcfcf", //[8] Absence🡪Stable🡪Absence
        ],
        'format': 'png'
    }
};




// all lulc images
var image = ee.Image(assetLulc);

var trajectoriesClassIds = {
    3: {
        'number_of_presence': null,
        'number_of_changes': null,
        'trajectories': null
    },
    4: {
        'number_of_presence': null,
        'number_of_changes': null,
        'trajectories': null
    },
    11: {
        'number_of_presence': null,
        'number_of_changes': null,
        'trajectories': null
    },
    12: {
        'number_of_presence': null,
        'number_of_changes': null,
        'trajectories': null
    },
    15: {
        'number_of_presence': null,
        'number_of_changes': null,
        'trajectories': null
    },
    18: {
        'number_of_presence': null,
        'number_of_changes': null,
        'trajectories': null
    },
    24: {
        'number_of_presence': null,
        'number_of_changes': null,
        'trajectories': null
    },
    33: {
        'number_of_presence': null,
        'number_of_changes': null,
        'trajectories': null
    },
}

// for each period in list
periods.forEach(
    function (period) {
        var count = period[1] - period[0] + 1;

        var bands = Array.apply(null, Array(count)).map(
            function (_, i) {
                return 'classification_' + (period[0] + i).toString();
            }
        );

        // lulc images 
        var imagePeriod = image.select(bands);

        // number of classes
        var nClasses = calculateNumberOfClasses(imagePeriod);
        print ("nclasses", nClasses)
        Map.addLayer (nClasses, {}, "number of classes")
print(nClasses, "nClasses")

 
        // number of changes
        var nChanges = calculateNumberOfChanges(imagePeriod);

        // stable
        // var stable = imagePeriod.select(0).multiply(nClasses.eq(1));

        // Map.addLayer(stable, visParams.stable, 'Stable', false);
        // Map.addLayer(nClasses, visParams.number_of_classes, 'Number of classes', false);

        // trajectories
        classIds.forEach(
            function (classList) {
                var classIdsMask = ee.List(bands).iterate(
                    function (band, allMasks) {
                        var mask = imagePeriod.select([band])
                            .remap(classList, ee.List.repeat(1, classList.length), 0);

                        return ee.Image(allMasks).addBands(mask);
                    },
                    ee.Image().select()
                );

                classIdsMask = ee.Image(classIdsMask).rename(bands);

                // number of presence
                var nPresence = calculateNumberOfPresence(classIdsMask);

                // nChanges in classList
                var nChanges = calculateNumberOfChanges(classIdsMask);
                // nChanges rules in the analisys
                var nChangesEq0 = nChanges.eq(0); //  no change
                var nChangesEq1 = nChanges.eq(1); //  1 change
                var nChangesGt1 = nChanges.gt(1); // >1 changes
                // var nChangesGt2 = nChanges.gt(2); // >2 changes

                // lulc classIds masks for the first year and last year 
                var t1 = classIdsMask.select(bands[0]);
                var tn = classIdsMask.select(bands[bands.length - 1]);

                // categories
                var abAbCh0 = t1.eq(0).and(nChangesEq0);
                var prPrCh0 = t1.eq(1).and(nChangesEq0);
                var abPrCh1 = t1.eq(0).and(nChangesEq1).and(tn.eq(1));
                var prAbCh1 = t1.eq(1).and(nChangesEq1).and(tn.eq(0));
                var abPrCh2 = t1.eq(0).and(nChangesGt1).and(tn.eq(1));
                var prAbCh2 = t1.eq(1).and(nChangesGt1).and(tn.eq(0));
                var abAbCh1 = t1.eq(0).and(nChangesGt1).and(tn.eq(0));
                var prPrCh1 = t1.eq(1).and(nChangesGt1).and(tn.eq(1));

                // (*) the classes Ab-Ab and Pr-Pr the classes were joined
                // var trajectories = ee.Image(0)
                //     .where(prAbCh1, 1)  //[1] Pr-Ab Ch=1 | Loss without Alternation
                //     .where(abPrCh1, 2)  //[2] Ab-Pr Ch=1 | Gain without Alternation
                //     .where(prAbCh2, 3)  //[3] Pr-Ab Ch>2 | Loss with Alternation
                //     .where(abPrCh2, 4)  //[4] Ab-Pr Ch>2 | Gain with Alternation
                //     .where(abAbCh1, 5)  //[5] Ab-Ab Ch>1 | Stable with Alternation (Ab-Ab)
                //     .where(prPrCh1, 5)  //[5] Pr-Pr Ch>1 | Stable with Alternation (Pr-Pr)
                //     .where(prPrCh0, 6)  //[6] Pr-Pr Ch=0 | Stable Presence
                //     .where(abAbCh0, 7); //[7] Ab-Ab Ch=0 | Stable Absence
                var trajectories = ee.Image(0)
                    .where(prAbCh1, 1)  // [1] Presence🡪Loss🡪Absence
                    .where(abPrCh1, 2)  // [2] Absence🡪Gain🡪Presence
                    .where(prAbCh2, 3)  // [3] Presence🡪Alternation🡪Loss🡪Absence
                    .where(abPrCh2, 4)  // [4] Absence🡪Alternation🡪Gain🡪Presence
                    .where(prPrCh1, 5)  // [5] Presence🡪Alternation🡪Presence
                    .where(abAbCh1, 6)  // [6] Absence🡪Alternation🡪Absence
                    .where(prPrCh0, 7)  // [7] Presence🡪Stable🡪Presence
                    .where(abAbCh0, 8); // [8] Absence🡪Stable🡪Absence

                trajectories = trajectories.rename('trajectories').selfMask();

                trajectoriesClassIds[classList[0]].number_of_presence = nPresence;
                trajectoriesClassIds[classList[0]].number_of_changes = nChanges;
                trajectoriesClassIds[classList[0]].trajectories = trajectories;
            }
        );
    }
);

var traj_for = trajectoriesClassIds[3].trajectories
var traj_pas = trajectoriesClassIds[15].trajectories
var traj_sav = trajectoriesClassIds[4].trajectories
var traj_gra = trajectoriesClassIds[12].trajectories
var traj_wat = trajectoriesClassIds[33].trajectories
var traj_urb = trajectoriesClassIds[24].trajectories
var traj_agr = trajectoriesClassIds[18].trajectories
var traj_wet = trajectoriesClassIds[11].trajectories

var trajectoriesComposite = ee.Image.cat(
  [traj_for, traj_pas,traj_sav,traj_gra,traj_wat,traj_urb, traj_agr, traj_wet ])
    .rename(["traj_for", "traj_pas", "traj_sav", "traj_gra", "traj_wat", "traj_urb", "traj_agr", "traj_wet"]);

print('trajectoriesComposite', trajectoriesComposite);

Map.addLayer(trajectoriesClassIds[3].number_of_changes, visParams.number_of_changes, 'Number of changes', false);
Map.addLayer(trajectoriesClassIds[3].number_of_presence, visParams.number_of_presence, 'Number of time points of presence', false);
Map.addLayer(trajectoriesClassIds[3].trajectories, visParams.trajectories, 'Trajectories_Flor', false);
Map.addLayer(trajectoriesClassIds[15].trajectories, visParams.trajectories, 'Trajectories_Pasture', false);
Map.addLayer(trajectoriesClassIds[4].trajectories, visParams.trajectories, 'Trajectories_Savana', false);
Map.addLayer(trajectoriesClassIds[12].trajectories, visParams.trajectories, 'Trajectories_Campos', false);
Map.addLayer(trajectoriesClassIds[33].trajectories, visParams.trajectories, 'Trajectories_rioslagos', false);
Map.addLayer(trajectoriesClassIds[24].trajectories, visParams.trajectories, 'Trajectories_urbano', false);
Map.addLayer(trajectoriesClassIds[18].trajectories, visParams.trajectories, 'Trajectories_Crops', false);
Map.addLayer(trajectoriesClassIds[11].trajectories, visParams.trajectories, 'Trajectories_Wetlands', false);


print("trajectoriesImage", trajectoriesImage)

/**
 * @description
 *    calculate area
 * 
 * @author
 *    João Siqueira
 * 
 */



// Asset mapbiomas (trajectories composite by class)
var asset = trajectoriesComposite

// Change the scale if you need.
var scale = 30;

// Define a list of classes to export
var classe = [
  'for', 'pas','sav', 'gra','wat','urb', 'agr', 'wet'
];

// Define a Google Drive output folder 
var driverFolder = 'AREA-EXPORT';


// Territory image
var territory = ee.Image(assetTerritories);

// LULC mapbiomas image
var mapbiomas = ee.Image(asset).selfMask();

// Image area in km2
var pixelArea = ee.Image.pixelArea().divide(1000000);

// Geometry to export
var geometry = trajectoriesImage.geometry();

/**
 * Convert a complex ob to feature collection
 * @param obj 
 */
 
 
var convert2table = function (obj) {

    obj = ee.Dictionary(obj);

    var territory = obj.get('territory');

    var classesAndAreas = ee.List(obj.get('groups'));

    var tableRows = classesAndAreas.map(
        function (classAndArea) {
            classAndArea = ee.Dictionary(classAndArea);

            var classId = classAndArea.get('class');
            var area = classAndArea.get('sum');

            var tableColumns = ee.Feature(null)
                .set('territory', territory)
                .set('class', classId)
                .set('area', area);

            return tableColumns;
        }
    );

    return ee.FeatureCollection(ee.List(tableRows));
};

/*
 * Calculate area crossing a cover map (deforestation, mapbiomas)
 * and a region map (states, biomes, municipalites)
 * @param image 
 * @param territory 
 * @param geometry
*/
var calculateArea = function (image, territory, geometry) {

    var reducer = ee.Reducer.sum().group(1, 'class').group(1, 'territory');

    var territotiesData = pixelArea.addBands(territory).addBands(image)
        .reduceRegion({
            reducer: reducer,
            geometry: geometry,
            scale: scale,
            maxPixels: 1e12
        });

    territotiesData = ee.List(territotiesData.get('groups'));

    var areas = territotiesData.map(convert2table);

    areas = ee.FeatureCollection(areas).flatten();

    return areas;
};

var areas = classe.map(
    function (classe) {
        var image = mapbiomas.select('traj_' + classe);

        var areas = calculateArea(image, territory, geometry);

        // set additional properties
        areas = areas.map(
            function (feature) {
                return feature.set('classe', classe);
            }
        );

        return areas;
    }
);

areas = ee.FeatureCollection(areas).flatten();

Export.table.toDrive({
    collection: areas,
    description: 'trajs_col10_biomes',
    folder: driverFolder,
    fileNamePrefix: 'trajs_col10_biomes',
    fileFormat: 'CSV'
});




// LEGEND

var nChangesLegend = Legend.getLegend(
    {
        "title": "Number of changes",
        "layers": [
            [visParams.number_of_changes.palette[0], 0, " no Change"],
            [visParams.number_of_changes.palette[1], 1, " 1 Change"],
            [visParams.number_of_changes.palette[2], 2, " 2 Changes"],
            [visParams.number_of_changes.palette[3], 3, " 3 Changes"],
            [visParams.number_of_changes.palette[4], 4, " 4 Changes"],
            [visParams.number_of_changes.palette[5], 5, " 5 Changes"],
            [visParams.number_of_changes.palette[6], 6, ">5 Changes"],
        ],
        "style": {
            "backgroundColor": "#21242E",
            "color": "#ffffff",
            "fontSize": '12px',
            "iconSize": '14px',
        },
        "orientation": "vertical"
    }
);

var nClassesLegend = Legend.getLegend(
    {
        "title": "Number of classes",
        "layers": [
            [visParams.number_of_classes.palette[1], 1, " 1 Class"],
            [visParams.number_of_classes.palette[2], 2, " 2 Classes"],
            [visParams.number_of_classes.palette[3], 3, " 3 Classes"],
            [visParams.number_of_classes.palette[4], 4, " 4 Classes"],
            [visParams.number_of_classes.palette[5], 5, ">4 Classes"],
        ],
        "style": {
            "backgroundColor": "#21242E",
            "color": "#ffffff",
            "fontSize": '12px',
            "iconSize": '14px',
        },
        "orientation": "vertical"
    }
);

var trajectoriesLegend = Legend.getLegend(
    {
        "title": "Trajectories",
        "layers": [
            [visParams.trajectories.palette[0], 0, "Mask"],
            [visParams.trajectories.palette[1], 1, "Presence🡪Loss🡪Absence"],
            [visParams.trajectories.palette[2], 2, "Absence🡪Gain🡪Presence"],
            [visParams.trajectories.palette[3], 3, "Presence🡪Alternation🡪Loss🡪Absence"],
            [visParams.trajectories.palette[4], 4, "Absence🡪Alternation🡪Gain🡪Presence"],
            [visParams.trajectories.palette[5], 5, "Presence🡪Alternation🡪Presence"],
            [visParams.trajectories.palette[6], 6, "Absence🡪Alternation🡪Absence"],
            [visParams.trajectories.palette[7], 7, "Presence🡪Stable🡪Presence"],
            [visParams.trajectories.palette[8], 8, "Absence🡪Stable🡪Absence"],
        ],
        "style": {
            "backgroundColor": "#21242E",
            "color": "#ffffff",
            "fontSize": '12px',
            "iconSize": '14px',
        },
        "orientation": "vertical"
    }
);

ColorRamp.init(
    {
        'orientation': 'horizontal',
        'backgroundColor': '21242E',
        'fontColor': 'ffffff',
        'height': '10px',
        'width': '250px',
    }
);

ColorRamp.add({
    'title': 'Number of time points of presence',
    'min': visParams.number_of_presence.min,
    'max': visParams.number_of_presence.max,
    'palette': visParams.number_of_presence.palette,
});

// Get legend widget
var colorRamp1 = ColorRamp.getWidget();

var mapbiomasLegend = Legend.getLegend(
    {
        "title": "MapBiomas",
        "layers": [
            [visParams.stable.palette[0], 0, 'Non Observed'],
            [visParams.stable.palette[3], 3, 'Forest Formation'],
            [visParams.stable.palette[4], 4, 'Savanna Formation'],
            [visParams.stable.palette[5], 5, 'Mangrove'],
            [visParams.stable.palette[49], 49, 'Wooded Restinga'],
            [visParams.stable.palette[11], 11, 'Wetland'],
            [visParams.stable.palette[12], 12, 'Grassland'],
            [visParams.stable.palette[32], 32, 'Salt flat'],
            [visParams.stable.palette[29], 29, 'Rocky outcrop'],
            [visParams.stable.palette[13], 13, 'Other Non Forest Natural Formation'],
            [visParams.stable.palette[18], 18, 'Agriculture'],
            [visParams.stable.palette[39], 39, 'Soybean'],
            [visParams.stable.palette[20], 20, 'Sugar Cane'],
            [visParams.stable.palette[40], 40, 'Rice'],
            [visParams.stable.palette[41], 41, ' Other Temporary Crops'],
            [visParams.stable.palette[46], 46, 'Coffee'],
            [visParams.stable.palette[47], 47, 'Citrus'],
            [visParams.stable.palette[48], 48, 'Other Perennial Crops'],
            [visParams.stable.palette[9], 9, 'Forest Plantation'],
            [visParams.stable.palette[15], 15, 'Pasture'],
            [visParams.stable.palette[21], 21, 'Mosaic of Agriculture and Pasture'],
            [visParams.stable.palette[22], 22, 'Non Vegetated Area'],
            [visParams.stable.palette[23], 23, 'Beach and Dune'],
            [visParams.stable.palette[24], 24, 'Urban Area'],
            [visParams.stable.palette[30], 30, 'Mining'],
            [visParams.stable.palette[25], 25, 'Other Non Vegetated Area'],
            [visParams.stable.palette[33], 33, 'River, Lake and Ocean'],
            [visParams.stable.palette[31], 31, 'Aquaculture'],
        ],
        "style": {
            "backgroundColor": "#ffffff",
            "color": "#212121",
            "fontSize": '12px',
            "iconSize": '14px',
        },
        "orientation": "vertical"
    }
);

var panel = ui.Panel({
    widgets: [
        trajectoriesLegend,
        nChangesLegend,
        // nClassesLegend,
        colorRamp1,
        // mapbiomasLegend
    ],
    style: {
        position: 'bottom-left',
        backgroundColor: '21242E',
    }
});

Map.add(panel);

var layersInspector = {

    data: {
        trajectories: trajectoriesClassIds[3].trajectories,
        number_of_changes: trajectoriesClassIds[3].number_of_changes,
        number_of_presence: trajectoriesClassIds[3].number_of_presence,
        point: null
    },

    trajectory_names: [
        'Mask',
        'Presence🡪Loss🡪Absence',
        'Absence🡪Gain🡪Presence',
        'Presence🡪Alternation🡪Loss🡪Absence',
        'Absence🡪Alternation🡪Gain🡪Presence',
        'Presence🡪Alternation🡪Presence',
        'Absence🡪Alternation🡪Absence',
        'Presence🡪Stable🡪Presence',
        'Absence🡪Stable🡪Absence',
    ],
    init: function () {
        layersInspector.ui.init();
    },

    getSamplePoint: function (image, points) {

        var sample = image.sampleRegions({
            'collection': points,
            'scale': 30,
            'geometries': true
        });

        return sample;
    },

    ui: {

        init: function () {

            layersInspector.ui.form.init();
            layersInspector.ui.activateMapOnClick();

        },

        activateMapOnClick: function () {

            Map.onClick(
                function (coords) {
                    layersInspector.data.point = ee.Geometry.Point(coords.lon, coords.lat);

                    layersInspector.ui.inspect(layersInspector.data.point);
                }
            );
        },

        refresh: function (trajectories, nChanges, nPresence) {

            trajectories.evaluate(
                function (trajectories) {
                    var value = trajectories.features[0].properties.trajectories;
                    layersInspector.ui.form.labelTrajectories.setValue('Trajectory: [' + value.toString() + '] ' + layersInspector.trajectory_names[value]);

                    layersInspector.ui.form.panelTrajectoriesColor.style()
                        .set('backgroundColor', visParams.trajectories.palette[value]);
                }
            );

            nChanges.evaluate(
                function (nChanges) {
                    var value = nChanges.features[0].properties.number_of_changes;
                    layersInspector.ui.form.labelnChanges.setValue('Number of changes: ' + value.toString());

                    layersInspector.ui.form.panelnChangesColor.style()
                        .set('backgroundColor', visParams.number_of_changes.palette[value]);
                }
            );

            nPresence.evaluate(
                function (nPresence) {

                    var value = nPresence.features[0].properties.number_of_presence;
                    var r = nPresence.features[0].properties['vis-red'];
                    var g = nPresence.features[0].properties['vis-blue'];
                    var b = nPresence.features[0].properties['vis-green'];
                    layersInspector.ui.form.labelnPresence.setValue('Number of time points of presence: ' + value.toString());

                    function componentToHex(c) {
                        var hex = c.toString(16);
                        return hex.length == 1 ? "0" + hex : hex;
                    }

                    function rgbToHex(r, g, b) {
                        return "#" + componentToHex(r) + componentToHex(g) + componentToHex(b);
                    }

                    layersInspector.ui.form.panelnPresenceColor.style()
                        .set('backgroundColor', rgbToHex(r, g, b));
                }
            );
        },

        inspect: function (point) {

            point = ee.FeatureCollection(layersInspector.data.point);

            var trajectories = layersInspector.getSamplePoint(layersInspector.data.trajectories, point);
            var nChanges = layersInspector.getSamplePoint(layersInspector.data.number_of_changes, point);
            var nPresence = layersInspector.getSamplePoint(layersInspector.data.number_of_presence.visualize({
                min: visParams.number_of_presence.min,
                max: visParams.number_of_presence.max,
                palette: visParams.number_of_presence.palette,
            }).addBands(layersInspector.data.number_of_presence), point);

            layersInspector.ui.refresh(trajectories, nChanges, nPresence);

        },

        form: {

            init: function () {

                layersInspector.ui.form.panelInspector.add(layersInspector.ui.form.panelTrajectories);
                layersInspector.ui.form.panelInspector.add(layersInspector.ui.form.panelnChanges);
                layersInspector.ui.form.panelInspector.add(layersInspector.ui.form.panelnPresence);

                layersInspector.ui.form.panelTrajectories.add(layersInspector.ui.form.panelTrajectoriesColor);
                layersInspector.ui.form.panelnChanges.add(layersInspector.ui.form.panelnChangesColor);
                layersInspector.ui.form.panelnPresence.add(layersInspector.ui.form.panelnPresenceColor);

                layersInspector.ui.form.panelTrajectories.add(layersInspector.ui.form.labelTrajectories);
                layersInspector.ui.form.panelnChanges.add(layersInspector.ui.form.labelnChanges);
                layersInspector.ui.form.panelnPresence.add(layersInspector.ui.form.labelnPresence);

                Map.add(layersInspector.ui.form.panelInspector);
            },

            panelInspector: ui.Panel({
                'layout': ui.Panel.Layout.flow('vertical'),
                'style': {
                    'width': '500px',
                    // 'height': '150px',
                    'position': 'bottom-right',
                    // 'margin': '0px 0px 0px 0px',
                    // 'padding': '0px',
                    'backgroundColor': '#21242E'
                },
            }),

            panelTrajectories: ui.Panel({
                'layout': ui.Panel.Layout.flow('horizontal'),
                'style': {
                    'backgroundColor': '#21242E'
                },
            }),

            panelnChanges: ui.Panel({
                'layout': ui.Panel.Layout.flow('horizontal'),
                'style': {
                    'backgroundColor': '#21242E'
                },
            }),

            panelnPresence: ui.Panel({
                'layout': ui.Panel.Layout.flow('horizontal'),
                'style': {
                    'backgroundColor': '#21242E'
                },
            }),

            panelTrajectoriesColor: ui.Panel({
                'layout': ui.Panel.Layout.flow('horizontal'),
                'style': {
                    'backgroundColor': '#cccccc',
                    'width': '14px',
                    'height': '14px',
                    'margin': '8px 0px 0px 0px'
                },
            }),

            panelnChangesColor: ui.Panel({
                'layout': ui.Panel.Layout.flow('horizontal'),
                'style': {
                    'backgroundColor': '#cccccc',
                    'width': '14px',
                    'height': '14px',
                    'margin': '8px 0px 0px 0px'
                },
            }),

            panelnPresenceColor: ui.Panel({
                'layout': ui.Panel.Layout.flow('horizontal'),
                'style': {
                    'backgroundColor': '#cccccc',
                    'width': '14px',
                    'height': '14px',
                    'margin': '8px 0px 0px 0px'
                },
            }),

            labelTrajectories: ui.Label('Trajectory: -', {
                'color': '#ffffff',
                'backgroundColor': '#21242E00',
                'fontSize': '12px'
            }),

            labelnChanges: ui.Label('Number of changes: -', {
                'color': '#ffffff',
                'backgroundColor': '#21242E00',
                'fontSize': '12px'
            }),

            labelnPresence: ui.Label('Number of time points of presence: -', {
                'color': '#ffffff',
                'backgroundColor': '#21242E00',
                'fontSize': '12px'
            }),

        }
    }
};

layersInspector.init();

var tsInspector = {

    options: {
        'title': 'Temporal series',
        'legend': 'none',
        'chartArea': {
            left: 50,
            right: 5,
        },
        'titleTextStyle': {
            color: '#ffffff',
            fontSize: 12,
            bold: true,
            italic: false
        },
        'tooltip': {
            textStyle: {
                fontSize: 10,
            },
            // isHtml: true
        },
        'backgroundColor': '#21242E',
        'pointSize': 6,
        'crosshair': {
            trigger: 'both',
            orientation: 'vertical',
            focused: {
                color: '#dddddd'
            }
        },
        'hAxis': {
            // title: 'Date', //muda isso aqui
            slantedTextAngle: 90,
            slantedText: true,
            textStyle: {
                color: '#ffffff',
                fontSize: 8,
                fontName: 'Arial',
                bold: false,
                italic: false
            },
            titleTextStyle: {
                color: '#ffffff',
                fontSize: 10,
                fontName: 'Arial',
                bold: true,
                italic: false
            },
            viewWindow: {
                max: 36,
                min: 0
            },
            gridlines: {
                color: '#21242E',
                interval: 1
            },
            minorGridlines: {
                color: '#21242E'
            }
        },
        'vAxis': {
            title: 'Class', // muda isso aqui
            textStyle: {
                color: '#ffffff',
                fontSize: 10,
                bold: false,
                italic: false
            },
            titleTextStyle: {
                color: '#ffffff',
                fontSize: 10,
                bold: false,
                italic: false
            },
            viewWindow: {
                max: 50,
                min: 0
            },
            gridlines: {
                color: '#21242E',
                interval: 2
            },
            minorGridlines: {
                color: '#21242E'
            }
        },
        'lineWidth': 0,
        // 'width': '300px',
        'height': '150px',
        'margin': '0px 0px 0px 0px',
        'series': {
            0: { color: '#21242E' }
        },

    },

    assets: {
        image: image,
        // imagef: image
    },

    data: {
        imagef: null,
        point: null
    },

    legend: {
        0: { 'color': mpbPalette[0], 'name': 'Non Observed' },
        3: { 'color': mpbPalette[3], 'name': 'Forest Formation' },
        4: { 'color': mpbPalette[4], 'name': 'Savanna Formation' },
        5: { 'color': mpbPalette[5], 'name': 'Mangrove' },
        49: { 'color': mpbPalette[49], 'name': 'Wooded Restinga' },
        11: { 'color': mpbPalette[11], 'name': 'Wetland' },
        12: { 'color': mpbPalette[12], 'name': 'Grassland' },
        32: { 'color': mpbPalette[32], 'name': 'Salt flat' },
        29: { 'color': mpbPalette[29], 'name': 'Rocky outcrop' },
        13: { 'color': mpbPalette[13], 'name': 'Other Non Forest Natural Formation' },
        18: { 'color': mpbPalette[18], 'name': 'Agriculture' },
        39: { 'color': mpbPalette[39], 'name': 'Soybean' },
        20: { 'color': mpbPalette[20], 'name': 'Sugar Cane' },
        40: { 'color': mpbPalette[40], 'name': 'Rice' },
        41: { 'color': mpbPalette[41], 'name': ' Other Temporary Crops' },
        46: { 'color': mpbPalette[46], 'name': 'Coffee' },
        47: { 'color': mpbPalette[47], 'name': 'Citrus' },
        48: { 'color': mpbPalette[48], 'name': 'Other Perennial Crops' },
        9: { 'color': mpbPalette[9], 'name': 'Forest Plantation' },
        15: { 'color': mpbPalette[15], 'name': 'Pasture' },
        21: { 'color': mpbPalette[21], 'name': 'Mosaic of Agriculture and Pasture' },
        22: { 'color': mpbPalette[22], 'name': 'Non Vegetated Area' },
        23: { 'color': mpbPalette[23], 'name': 'Beach and Dune' },
        24: { 'color': mpbPalette[24], 'name': 'Urban Area' },
        30: { 'color': mpbPalette[30], 'name': 'Mining' },
        25: { 'color': mpbPalette[25], 'name': 'Other Non Vegetated Area' },
        33: { 'color': mpbPalette[33], 'name': 'River, Lake and Ocean' },
        31: { 'color': mpbPalette[31], 'name': 'Aquaculture' },
    },

    loadData: function () {
        tsInspector.data.image = ee.Image(tsInspector.assets.image);
        // Inspector.data.imagef = ee.Image(Inspector.assets.imagef);
    },

    init: function () {
        tsInspector.loadData();
        tsInspector.ui.init();
    },

    getSamplePoint: function (image, points) {

        var sample = image.sampleRegions({
            'collection': points,
            'scale': 30,
            'geometries': true
        });

        return sample;
    },

    ui: {

        init: function () {

            tsInspector.ui.form.init();
            tsInspector.ui.activateMapOnClick();

        },

        activateMapOnClick: function () {

            Map.onClick(
                function (coords) {
                    var point = ee.Geometry.Point(coords.lon, coords.lat);

                    var bandNames = tsInspector.data.image.bandNames();

                    var newBandNames = bandNames.map(
                        function (bandName) {
                            var name = ee.String(ee.List(ee.String(bandName).split('_')).get(1));

                            return name;
                        }
                    );

                    var image = tsInspector.data.image.select(bandNames, newBandNames);

                    tsInspector.ui.inspect(tsInspector.ui.form.chartInspector, image, point, 1.0);
                }
            );
        },

        refreshGraph: function (chart, sample, opacity) {

            sample.evaluate(
                function (featureCollection) {

                    if (featureCollection !== null) {
                        var pixels = featureCollection.features.map(
                            function (features) {
                                return features.properties;
                            }
                        );

                        var bands = Object.getOwnPropertyNames(pixels[0]);

                        // Add class value
                        var dataTable = bands.map(
                            function (band) {
                                var value = pixels.map(
                                    function (pixel) {
                                        return pixel[band];
                                    }
                                );

                                return [band].concat(value);
                            }
                        );

                        // Add point style and tooltip
                        dataTable = dataTable.map(
                            function (point) {
                                var color = tsInspector.legend[point[1]].color;
                                var name = tsInspector.legend[point[1]].name;
                                var value = String(point[1]);

                                var style = 'point {size: 4; fill-color: ' + color + '; opacity: ' + opacity + '}';
                                var tooltip = 'year: ' + point[0] + ', class: [' + value + '] ' + name;

                                return point.concat(style).concat(tooltip);
                            }
                        );

                        var headers = [
                            'serie',
                            'id',
                            { 'type': 'string', 'role': 'style' },
                            { 'type': 'string', 'role': 'tooltip' }
                        ];

                        dataTable = [headers].concat(dataTable);

                        chart.setDataTable(dataTable);

                    }
                }
            );
        },

        refreshMap: function () {

            var pointLayer = Map.layers().filter(
                function (layer) {
                    return layer.get('name') === 'Point';
                }
            );

            if (pointLayer.length > 0) {
                Map.remove(pointLayer[0]);
                Map.addLayer(tsInspector.data.point, {}, 'Point');
            } else {
                Map.addLayer(tsInspector.data.point, {}, 'Point');
            }

        },

        inspect: function (chart, image, point, opacity) {

            // aqui pode fazer outras coisas além de atualizar o gráfico
            tsInspector.data.point = tsInspector.getSamplePoint(image, ee.FeatureCollection(point));

            tsInspector.ui.refreshMap(tsInspector.data.point);
            tsInspector.ui.refreshGraph(chart, tsInspector.data.point, opacity);

        },

        form: {

            init: function () {

                tsInspector.ui.form.panelInspector.add(tsInspector.ui.form.chartInspector);
                // Inspector.ui.form.panelInspector.add(Inspector.ui.form.chartInspectorf);

                tsInspector.options.title = 'Temporal series';
                tsInspector.ui.form.chartInspector.setOptions(tsInspector.options);

                Map.add(tsInspector.ui.form.panelInspector);
            },

            panelInspector: ui.Panel({
                'layout': ui.Panel.Layout.flow('vertical'),
                'style': {
                    'width': '500px',
                    // 'height': '200px',
                    'position': 'bottom-right',
                    'margin': '0px 0px 0px 0px',
                    'padding': '0px',
                    'backgroundColor': '#21242E'
                },
            }),

            chartInspector: ui.Chart([
                ['Serie', ''],
                ['', -1000], // número menor que o mínimo para não aparecer no gráfico na inicialização
            ]),

            // chartInspectorf: ui.Inspector([
            //     ['Serie', ''],
            //     ['', -1000], // número menor que o mínimo para não aparecer no gráfico na inicialização
            // ])
        }
    }
};

tsInspector.init();

//
var Chart = {

    options: {
        'title': 'Trajectories Analysis',
        'titleTextStyle': {
            color: '#ffffff',
            // fontSize: 10,
            bold: true,
            italic: false
        },

        'legend': {
            position: 'top',
            maxLines: 1,
            textStyle: {
                color: '#ffffff',
                // fontSize: 8,
                // fontName: 'Arial',
                bold: false,
                italic: false
            }
        },
        'bar': { 'groupWidth': '100%' },
        'isStacked': true,
        'chartArea': {
            left: 50,
            right: 5,
            bottom: 100,
        },
        'tooltip': {
            textStyle: {
                fontSize: 10,
            },
            // isHtml: true
        },
        'backgroundColor': '#21242E',
        'pointSize': 6,
        'crosshair': {
            trigger: 'both',
            orientation: 'vertical',
            focused: {
                color: '#dddddd'
            }
        },
        'hAxis': {
            title: 'Time Intervals', //muda isso aqui
            slantedTextAngle: 90,
            slantedText: true,
            textStyle: {
                color: '#ffffff',
                fontSize: 10,
                fontName: 'Arial',
                bold: false,
                italic: false
            },
            titleTextStyle: {
                color: '#ffffff',
                // fontSize: 10,
                fontName: 'Arial',
                bold: true,
                italic: false
            },
            // viewWindow: {
            //     max: 36,
            //     min: 0
            // },
            gridlines: {
                color: '#21242E',
                interval: 1
            },
            minorGridlines: {
                color: '#21242E'
            }
        },
        'vAxis': {
            title: 'Annual Loss and Gain (km2)',
            textStyle: {
                color: '#ffffff',
                fontSize: 10,
                bold: false,
                italic: false
            },
            titleTextStyle: {
                color: '#ffffff',
                // fontSize: 10,
                bold: false,
                italic: false
            },
            // viewWindow: {
            //     max: 200000,
            //     min: -200000
            // },
            baselineColor: '#ffffff',
            gridlines: {
                color: '#21242E',
                interval: 1
            },
            minorGridlines: {
                color: '#21242E'
            },
            format: 'short'
        },
        'lineWidth': 0,
        // 'width': '300px',
        'height': '300px',
        'margin': '0px 0px 0px 0px',
        // 'series': {
        //     0: { 'color': "#941004" }, // [11] Loss (Loss without Alternation)
        //     1: { 'color': "#f5261b" }, // [13] Loss (Loss with Alternation)
        //     2: { 'color': "#14a5e3" }, // [14] Loss (Gain with Alternation)
        //     3: { 'color': "#8b8000" }, // [15] Loss (Stable with Alternation)
        //     4: { 'color': "#ffff00" }, // [16] Loss (Stable with Alternation)
        //     5: { 'color': "#020e7a" }, // [22] Gain (Gain without Alternation) 
        //     6: { 'color': "#f5261b" }, // [23] Gain (Loss with Alternation)
        //     7: { 'color': "#14a5e3" }, // [24] Gain (Gain with Alternation) 
        //     8: { 'color': "#8b8000" }, // [25] Gain (Stable with Alternation) 
        //     9: { 'color': "#ffff00" }, // [26] Gain (Stable with Alternation) 
        // },
        'series': {
            0: { 'color': "#941004" }, // [11] Loss (Loss without Alternation)
            1: { 'color': "#f5261b" }, // [13] Loss (Loss with Alternation)
            2: { 'color': "#14a5e3" }, // [14] Loss (Gain with Alternation)
            3: { 'color': "#ffff00" }, // [16] Loss (Stable with Alternation)
            4: { 'color': "#020e7a" }, // [22] Gain (Gain without Alternation) 
            5: { 'color': "#f5261b" }, // [23] Gain (Loss with Alternation)
            6: { 'color': "#14a5e3" }, // [24] Gain (Gain with Alternation) 
            7: { 'color': "#ffff00" }, // [26] Gain (Stable with Alternation) 
        },

    },

    assets: {
        tables: {
            biomes: 'users/joaovsiqueira1/brazil-biomes-trajectorties-3c',
            country: 'users/joaovsiqueira1/brazil-country-trajectorties-3c'
        },
        biomes: 'projects/mapbiomas-workspace/AUXILIAR/biomas-2019-raster'
    },

    data: {
        table: null,
        biomes: null
    },

    variables: {
        territory_id: 'Brazil',
        trajectory_ids: [
            11, // Loss (Presence🡪Loss🡪Absence)
            13, // Loss (Presence🡪Alternation🡪Loss🡪Absence)
            14, // Loss (Absence🡪Alternation🡪Gain🡪Presence)
            15, // Loss (Presence🡪Alternation🡪Presence)
            16, // Loss (Absence🡪Alternation🡪Absence)
            22, // Gain (Absence🡪Gain🡪Presence)
            23, // Gain (Presence🡪Alternation🡪Loss🡪Absence)
            24, // Gain (Absence🡪Alternation🡪Gain🡪Presence)
            25, // Gain (Presence🡪Alternation🡪Presence)
            26, // Gain (Absence🡪Alternation🡪Absence)
        ],
        trajectory_names: [
            'L.Presence🡪Loss🡪Absence',
            'L.Presence🡪Alternation🡪Loss🡪Absence',
            'L.Absence🡪Alternation🡪Gain🡪Presence',
            // 'L.Presence🡪Alternation🡪Presence',
            'L.Absence🡪Alternation🡪Absence',
            'G.Absence🡪Gain🡪Presence',
            'G.Presence🡪Alternation🡪Loss🡪Absence',
            'G.Absence🡪Alternation🡪Gain🡪Presence',
            // 'G.Presence🡪Alternation🡪Presence',
            'G.Absence🡪Alternation🡪Absence',
        ],
        class_id: 3,
        biome_ids: {
            'Brazil': 0,
            'AMAZÔNIA': 1,
            'CAATINGA': 5,
            'CERRADO': 4,
            'MATA ATLÂNTICA': 2,
            'PAMPA': 6,
            'PANTANAL': 3
        }
    },

    periods: [
        "1985-1986",
        "1986-1987",
        "1987-1988",
        "1988-1989",
        "1989-1990",
        "1990-1991",
        "1991-1992",
        "1992-1993",
        "1993-1994",
        "1994-1995",
        "1995-1996",
        "1996-1997",
        "1997-1998",
        "1998-1999",
        "1999-2000",
        "2000-2001",
        "2001-2002",
        "2002-2003",
        "2003-2004",
        "2004-2005",
        "2005-2006",
        "2006-2007",
        "2007-2008",
        "2008-2009",
        "2009-2010",
        "2010-2011",
        "2011-2012",
        "2012-2013",
        "2013-2014",
        "2014-2015",
        "2015-2016",
        "2016-2017",
        "2017-2018",
        "2018-2019",
        "2019-2020",
        "2020-2021",
        "2021-2022",
        "2022-2023"
    ],

    loadData: function () {
        Chart.data.table = ee.FeatureCollection(Chart.assets.tables.country);
        Chart.data.biomes = ee.Image(Chart.assets.biomes);
    },

    init: function () {
        Chart.loadData();
        Chart.ui.init();
    },

    ui: {

        init: function () {

            Chart.ui.form.init();

            Map.addLayer(Chart.data.biomes.eq(0).selfMask(), { opacity: 0.9, palette: 'ffffff,21242E' }, Chart.variables.territory_id);

            Chart.ui.refreshGraph(
                Chart.variables.territory_id,
                Chart.variables.trajectory_ids,
                Chart.variables.class_id
            );

        },

        refreshMap: function (territory_id, class_id) {
            Map.layers().forEach(
                function (layer) {
                    if (territory_id) {
                        if (layer.get('name') === Chart.variables.territory_id) {
                            if (territory_id === 'Brazil') {
                                layer.set('eeObject', Chart.data.biomes.eq(Chart.variables.biome_ids[territory_id]).selfMask());
                            } else {
                                layer.set('eeObject', Chart.data.biomes.neq(Chart.variables.biome_ids[territory_id]).selfMask());
                            }
                            layer.set('name', territory_id);
                        }
                    }

                    if (class_id) {
                        if (class_id !== Chart.variables.class_id) {
                            if (layer.get('name') === 'Trajectories') {
                                layer.set('eeObject', trajectoriesClassIds[class_id].trajectories);
                            }
                            if (layer.get('name') === 'Number of changes') {
                                layer.set('eeObject', trajectoriesClassIds[class_id].number_of_changes);
                            }
                            if (layer.get('name') === 'Number of time points of presence') {
                                layer.set('eeObject', trajectoriesClassIds[class_id].number_of_presence);
                            }
                        }
                    }

                }
            );
        },

        refreshGraph: function (territory_id, trajectory_ids, class_id) {

            var table = Chart.data.table
                .filter(ee.Filter.eq('name_en', territory_id))
                .filter(ee.Filter.eq('class_ids', class_id))
                .filter(ee.Filter.inList('trajectory_id', trajectory_ids));

            table.sort('trajectory_id').evaluate(
                function (featureCollection) {

                    if (featureCollection !== null) {

                        var properties = featureCollection.features.map(
                            function (features) {
                                return features.properties;
                            }
                        );

                        // Add class value
                        var dataTable = Chart.periods.map(
                            function (period) {
                                var value = properties.map(
                                    function (prop) {

                                        var area = prop[period];

                                        if ([11, 13, 14, 15, 16].indexOf(prop.trajectory_id) !== -1) {
                                            area = -1 * area;
                                        }

                                        return Math.floor(area / 100); // convert to km2
                                    }
                                );

                                return [period.slice(2, 4) + '-' + period.slice(7, 9)].concat(value).concat('stroke-width:0');
                            }
                        );

                        var headers = ["Time Intervals"].concat(Chart.variables.trajectory_names).concat({ 'role': 'style' });

                        dataTable = [headers].concat(dataTable);
                        // print(dataTable);
                        Chart.ui.form.chartTrajectories.setDataTable(dataTable);

                    }
                }
            );
        },

        form: {

            init: function () {

                Chart.ui.form.panelSelectors.add(Chart.ui.form.selectTerritory);
                Chart.ui.form.panelSelectors.add(Chart.ui.form.selectClass);
                Chart.ui.form.panelChart.add(Chart.ui.form.panelSelectors);
                Chart.ui.form.panelChart.add(Chart.ui.form.chartTrajectories);

                Chart.options.title = 'Trajectories Analysis';
                Chart.ui.form.chartTrajectories.setOptions(Chart.options);

                Map.add(Chart.ui.form.panelChart);
            },

            panelChart: ui.Panel({
                'layout': ui.Panel.Layout.flow('vertical'),
                'style': {
                    'width': '500px',
                    // 'height': '200px',
                    'position': 'bottom-right',
                    'margin': '0px 0px 0px 0px',
                    'padding': '0px',
                    'backgroundColor': '#21242E'
                },
            }),

            panelSelectors: ui.Panel({
                'layout': ui.Panel.Layout.flow('horizontal'),
                'style': {
                    'margin': '0px 0px 0px 0px',
                    'padding': '0px',
                    'backgroundColor': '#21242E00'
                },
            }),

            chartTrajectories: ui.Chart([
                ["Time Intervals", ""],
                ['', 0],
            ], 'ColumnChart'),

            selectTerritory: ui.Select({
                'items': [
                    { value: 'Brazil', label: 'Brazil' },
                    { value: 'AMAZÔNIA', label: 'Amazon' },
                    { value: 'CAATINGA', label: 'Caatinga' },
                    { value: 'CERRADO', label: 'Cerrado' },
                    { value: 'MATA ATLÂNTICA', label: 'Atlantic Forest' },
                    { value: 'PAMPA', label: 'Pampa' },
                    { value: 'PANTANAL', label: 'Pantanal' }
                ],
                'value': 'Brazil',
                'onChange': function (value) {

                    Chart.ui.refreshMap(value, false);

                    Chart.variables.territory_id = value;

                    if (value == 'Brazil') {
                        Chart.data.table = ee.FeatureCollection(Chart.assets.tables.country);
                    } else {
                        Chart.data.table = ee.FeatureCollection(Chart.assets.tables.biomes);
                    }

                    Chart.ui.refreshGraph(
                        Chart.variables.territory_id,
                        Chart.variables.trajectory_ids,
                        Chart.variables.class_id
                    );

                },
                'style': {
                    'width': '150px',
                    'backgroundColor': '#21242E66',
                    'color': '#21242E',
                }
            }),
            selectClass: ui.Select({
                'items': [
                    { label: 'Forest', value: 3 },
                    { label: 'Pasture', value: 15 },
                    { label: 'Agriculture', value: 18 },
                    { label: 'Water', value: 33 },
                    { label: 'Savanna', value: 4 },
                    { label: 'Grassland', value: 12 },
                    { label: 'Urban', value: 24 },
                ],
                'value': 3,
                'onChange': function (value) {

                    Chart.ui.refreshMap(false, value);

                    Chart.variables.class_id = value;

                    Chart.ui.refreshGraph(
                        Chart.variables.territory_id,
                        Chart.variables.trajectory_ids,
                        Chart.variables.class_id
                    );

                    layersInspector.data.trajectories = trajectoriesClassIds[value].trajectories;
                    layersInspector.data.number_of_changes = trajectoriesClassIds[value].number_of_changes;
                    layersInspector.data.number_of_presence = trajectoriesClassIds[value].number_of_presence;

                    if (layersInspector.data.point !== null) {
                        layersInspector.ui.inspect(layersInspector.data.point);
                    }
                },
                'style': {
                    'width': '150px',
                    'backgroundColor': '#21242E66',
                    'color': '#21242E',
                }
            })

        }
    }
};

Chart.init();

Map.setOptions({
    'styles': {
        'Dark': Mapp.getStyle('Dark')
    }
});

Map.setCenter(-46.32, -14);

// Create an empty image into which to paint the features, cast to byte.
var empty = ee.Image().byte();

// Paint all the polygon edges with the same number and width, display.
var outline = empty.paint({
  featureCollection: estados,
  color: 1,
  width: 2
});

Map.addLayer(outline, {palette: '141414'}, 'estados_limites');
