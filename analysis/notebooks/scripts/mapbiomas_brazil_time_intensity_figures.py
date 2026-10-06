"""Draws the time-intensity figures from the exported GeoJSON.

Run from this directory, with the project venv:
    ../../.venv/bin/python mapbiomas_brazil_time_intensity_figures.py

Reads the same files as the table script, so the figures never disagree with the xlsx.
"""
import itertools
import os
import sys

import matplotlib

matplotlib.use('Agg')

import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                '..', '..', 'statistics'))

import config  # noqa: E402
import tables  # noqa: E402
import time_intensity as ti  # noqa: E402
import plots  # noqa: E402

CATEGORIES = ['COUNTRY', 'REFINED_BIOME']

PRODUCT = 'INTENSIDADE-TEMPO'

FILE_LABEL = 'time.intensity'

PATH = '../../data/JSON/{}/{}-{}/*{}*'

OUTPUT_FOLDER = '../../data/FIGURES'

# Grouped as {territory}/{grid}/: one flat directory of 139 files is not navigable.
FOLDER_BY_TERRITORY = True
FOLDER_BY_GRID = True

OUTPUT_VERSION = '1'

# PNG only. The vector PDF of these figures is slow to write and doubles the file count;
# add 'pdf' back here when a vector version is needed for submission.
FORMATS = ('png',)

# 'complete' -> two A4 figures per (territory, grid), both 2 columns by 4 rows: one with
#               the coloured change charts, one with the grey components. Split because
#               the pair does not fit an A4 page at a legible size; cell positions match
#               between them, so panel (c) is the same class in both.
# 'panel'    -> the 8 classes as plain subplots, no components
# 'single'   -> one figure per (territory, class, grid)
# 'components-bar' -> ONE axes per territory holding every class as a column, the three
#               components stacked, with L or G over each column for the side the Quantity
#               component falls on. Reads across classes in a way the eight separate panels
#               cannot, which is what the unified-size denominator exists to allow.
# Only the two A4 grid figures and the components bar chart. 'panel' is the pre-A4 large
# grid, redundant with the A4 trajectories figure; 'single' is one figure per class, set
# aside for now.
FIGURE_MODES = ('complete', 'components-bar')

# Palatino 10 pt, black, as the paper sets its figures
PAPER_STYLE = True

COLUMNS = 2

# Both y-axis versions are produced. A free axis shows how each class changed over time;
# a shared one shows which class changes more, at the cost of the small classes' detail.
# Neither answers the other's question, so the pair is written rather than a choice made.
Y_AXIS_VERSIONS = (('free', False), ('sharedy', True))

CLASS_ORDER = [name for _, _, name in config.INTENSITY_CLASS_IDS]


def slug(value):
    return str(value).lower().replace(' ', '-').replace('_', '-')


def outputPath(territory, grid, name):
    """Where a figure goes: OUTPUT_FOLDER/{territory}/{grid}/, either level optional.

    The file name still carries the territory and the grid, so a figure pulled out of the
    tree and sent to someone on its own is still self-describing.
    """

    partes = [OUTPUT_FOLDER]

    if FOLDER_BY_TERRITORY:
        partes.append(slug(territory))

    # grid is None for figures that do not depend on the interval grid
    if FOLDER_BY_GRID and grid is not None:
        partes.append(grid)

    partes.append(name)

    return os.path.join(*partes)


def load():
    df = tables.loadDataFrame(
        pathTemplate=PATH,
        categories=CATEGORIES,
        product=PRODUCT,
        version=config.OUTPUT_VERSION,
        fileLabel=FILE_LABEL,
        valueName='composite_id',
        extraProperties=('grid',))

    return ti.prepare(df)


def territoryKeys(df):
    return (df[['category', 'feature_id']]
            .drop_duplicates()
            .sort_values(['category', 'feature_id'])
            .itertuples(index=False))


def subset(table, category, feature_id, class_name=None):
    rows = table[(table['category'] == category)
                 & (table['feature_id'] == feature_id)]

    if class_name is not None:
        rows = rows[rows['class_name'] == class_name]

    return rows


def averagesFor(averages, category, feature_id, class_name):
    rows = averages[(averages['category'] == category)
                    & (averages['feature_id'] == feature_id)
                    & (averages['class_name'] == class_name)]

    return None if rows.empty else rows.iloc[0]


def captionsPath():
    return os.path.join(OUTPUT_FOLDER, 'captions.txt')


def writeCaptions(entries):
    """Writes every figure caption to one text file.

    The captions are typeset as running text by the journal rather than drawn on the
    figure, so they are collected here instead of rendered.
    """

    folder = os.path.dirname(captionsPath())

    if folder and not os.path.isdir(folder):
        os.makedirs(folder)

    with open(captionsPath(), 'w') as handle:
        handle.write('Figure captions\n')
        handle.write('=' * 70 + '\n\n')

        for name, caption in entries:
            handle.write('{}\n{}\n\n'.format(name, caption))

    print('{} ({} captions)'.format(captionsPath(), len(entries)))


def main():
    if PAPER_STYLE:
        plots.usePaperStyle()

    captions = []

    df = load()

    averages = ti.averageLines(df)

    components = ti.componentsOfChange(df)
    ti.checkComponents(components)

    # Outside the grid loop on purpose. The components use the whole 1985-2024 extent, so
    # they do not depend on the interval grid: drawn inside the loop, the 5y and 10y files
    # come out byte-identical, which is exactly what the per-panel components figure does.
    if 'components-bar' in FIGURE_MODES:
        for category, feature_id in territoryKeys(components):

            territory = config.territoryName(category, feature_id)

            fig = plots.componentsByClassFigure(
                components[(components['category'] == category)
                           & (components['feature_id'] == feature_id)],
                classOrder=CLASS_ORDER)

            nome = 'components-by-class-{}-v{}'.format(slug(territory), OUTPUT_VERSION)

            plots.saveFigure(fig, outputPath(territory, None, nome), FORMATS)

            captions.append((
                '{}.png'.format(nome),
                plots.componentsByClassCaption(territory=territory,
                                               classCount=len(CLASS_ORDER))))

    for grid, intervals in config.INTERVAL_GRIDS.items():

        table = ti.buildIntensityTable(df, grid)

        label = '{}-year'.format(intervals[0][1] - intervals[0][0])

        for category, feature_id in territoryKeys(table):

            territory = config.territoryName(category, feature_id)

            if 'complete' in FIGURE_MODES:
                for (versao, sharedY), kind in itertools.product(
                        Y_AXIS_VERSIONS, ('trajectories', 'components')):
                    fig = plots.plotClassGrid(
                        kind,
                        table=table[(table['category'] == category)
                                    & (table['feature_id'] == feature_id)],
                        components=components[(components['category'] == category)
                                              & (components['feature_id'] == feature_id)],
                        averages=averages[(averages['category'] == category)
                                          & (averages['feature_id'] == feature_id)],
                        classOrder=CLASS_ORDER,
                        territory=territory,
                        gridLabel=label,
                        columns=COLUMNS,
                        sharedY=sharedY)

                    nome = 'time-intensity-a4-{}-{}-{}-{}-v{}'.format(
                        kind, versao, grid, slug(territory), OUTPUT_VERSION)

                    plots.saveFigure(fig, outputPath(territory, grid, nome), FORMATS)

                    captions.append((
                        '{}.png'.format(nome),
                        plots.captionFor(kind, label, territory=territory,
                                         classCount=len(CLASS_ORDER),
                                         sharedY=sharedY)))

            if 'panel' in FIGURE_MODES:
                fig, axes = plt.subplots(4, 2, figsize=(14, 16), sharey=SHARE_Y)

                for ax, class_name in zip(axes.ravel(), CLASS_ORDER):
                    rows = subset(table, category, feature_id, class_name)

                    # no per-axes legend here: the figure carries one at the foot
                    plots.plotTimeIntensity(
                        ax, rows,
                        averagesFor(averages, category, feature_id, class_name),
                        title=plots.CLASS_LABELS.get(class_name, class_name))

                fig.suptitle('{} — {} intervals'.format(territory, label),
                             fontsize=13, y=0.995)

                # reserve the bottom strip first, so the legend never lands on the
                # last row of subplots
                fig.tight_layout(rect=(0, 0.075, 1, 0.985))

                fig.legend(handles=plots.legendHandles(), loc='lower center',
                           ncol=3, frameon=False, fontsize=9,
                           bbox_to_anchor=(0.5, 0.022))
                fig.text(0.5, 0.004, plots.figureCaption(label), fontsize=8,
                         color=plots.INK_MUTED, ha='center')

                plots.saveFigure(fig, outputPath(
                    territory, grid, 'time-intensity-panel-{}-{}-v{}'.format(
                        grid, slug(territory), OUTPUT_VERSION)), FORMATS)

            if 'single' in FIGURE_MODES:
                for class_name in CLASS_ORDER:
                    rows = subset(table, category, feature_id, class_name)

                    if rows.empty:
                        continue

                    # (a) change per interval, (b) components over the whole extent,
                    # side by side as in the paper's figures
                    fig = plt.figure(figsize=(11, 5.6))
                    layout = fig.add_gridspec(1, 2, width_ratios=[3.1, 1.0],
                                              wspace=0.30)

                    ax = fig.add_subplot(layout[0])
                    axComponents = fig.add_subplot(layout[1])

                    # Fix the axes geometry BEFORE drawing. plotTimeIntensity measures
                    # the legend to decide how much headroom it needs, and resizing the
                    # axes afterwards would invalidate that measurement.
                    fig.subplots_adjust(left=0.085, right=0.975, top=0.87,
                                        bottom=0.30, wspace=0.30)

                    plots.plotTimeIntensity(
                        ax, rows,
                        averagesFor(averages, category, feature_id, class_name),
                        showLegend=True, panelLabel='(a)')

                    parte = averagesFor(components, category, feature_id, class_name)

                    if parte is not None:
                        plots.plotComponents(axComponents, parte, panelLabel='(b)')
                    else:
                        axComponents.set_axis_off()

                    fig.suptitle('{} — {}, {} intervals'.format(
                        plots.CLASS_LABELS.get(class_name, class_name),
                        territory, label), fontsize=11, y=0.99)

                    fig.text(0.5, 0.025, plots.figureCaption(label), fontsize=7.5,
                             color=plots.INK_MUTED, ha='center', wrap=True)

                    plots.saveFigure(fig, outputPath(
                        territory, grid, 'time-intensity-{}-{}-{}-v{}'.format(
                            grid, slug(territory), slug(class_name),
                            OUTPUT_VERSION)), FORMATS)


    writeCaptions(captions)


if __name__ == '__main__':
    main()
