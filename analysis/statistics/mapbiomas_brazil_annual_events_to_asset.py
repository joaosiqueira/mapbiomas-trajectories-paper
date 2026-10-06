"""Exports the base trajectory and the 39 annual event bands, one image per class.

Feeds the time-intensity figures. Python port of what used to be a Code Editor script;
see annual_events.py for why.

    python mapbiomas_brazil_annual_events_to_asset.py --dry-run   # inspect, queue nothing
    python mapbiomas_brazil_annual_events_to_asset.py             # queue the 8 exports

The output folder must exist first:
    earthengine create folder projects/YOUR-PROJECT/assets/trajectories-c10
    earthengine create folder projects/YOUR-PROJECT/assets/trajectories-c10/annual_events
"""
import argparse
import sys

import ee

import config
import annual_events
import ee_init

SCALE = 30


def exportRegion():
    """Same bbox as the other collection 10 exports.

    Built lazily: an ee.Geometry at module level would be constructed before
    ee.Initialize() runs, and fail.
    """

    return ee.Geometry.Polygon(
        [
            [
                [-74.34415028048886, 6.041474308055545],
                [-74.34415028048886, -34.38941142226404],
                [-34.17813465548886, -34.38941142226404],
                [-34.17813465548886, 6.041474308055545]
            ]
        ], None, False
    )


def parseArguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run', action='store_true',
                        help='describe what would be exported and queue nothing')
    parser.add_argument('--classes', nargs='*', default=None,
                        help='limit to these class names (default: all 8)')
    return parser.parse_args()


def classesToExport(selected):
    classes = config.INTENSITY_CLASS_IDS

    if not selected:
        return classes

    known = {name for _, _, name in classes}
    unknown = set(selected) - known

    if unknown:
        raise SystemExit('unknown class names: {}\nknown: {}'.format(
            sorted(unknown), sorted(known)))

    return [item for item in classes if item[2] in selected]


def main():
    arguments = parseArguments()

    # reads the Cloud project from EE_PROJECT (see ee_init.py)
    project = ee_init.initialize()

    if project:
        print('Earth Engine project: {}\n'.format(project))

    classes = classesToExport(arguments.classes)

    # built once and shared by every class, so the remap is not repeated per class
    lulc = annual_events.remappedLulc()

    for _, class_id, class_name in classes:

        image = annual_events.buildClassImage(class_id, class_name, lulc=lulc)

        target = annual_events.assetId(class_name)

        description = 'annual_events_{}_v{}'.format(
            class_name, config.ANNUAL_EVENTS_VERSION)

        if arguments.dry_run:
            bands = image.bandNames().getInfo()
            print('{:<22} {:>3} bands  {} ... {}  -> {}'.format(
                class_name, len(bands), bands[0], bands[-1], target))
            continue

        task = ee.batch.Export.image.toAsset(
            image=image,
            description=description,
            assetId=target,
            pyramidingPolicy={'.default': 'mode'},
            region=exportRegion(),
            scale=SCALE,
            maxPixels=1e13,
        )

        task.start()

        print('queued {} -> {}'.format(description, target))

    if arguments.dry_run:
        print('\ndry run: nothing was queued')
    else:
        print('\n{} tasks queued'.format(len(classes)))


if __name__ == '__main__':
    sys.exit(main())
