"""Draws the time-intensity figure of Bilintoh, Pontius & Zhang (2024).

The geometry carries meaning, so it is worth stating what each dimension is:

    bar WIDTH   = duration of the interval, in calendar years
    bar HEIGHT  = annual gross change, as % of the unified size, per year
    bar AREA    = width x height = total change during the interval
    above zero  = gain, below zero = loss
    segment colour = the pixel's trajectory over the whole 1985-2024 extent

Because width is in the same data units as the x axis, matplotlib gives the area
identity for free - as long as the width is exactly `year_end - year_start` with no
cosmetic inset. Do not add one.

On colour: the 8-colour trajectory palette is fixed by the published paper and is not
ours to change. Running it through a categorical-palette validator, the colourblind
separation passes comfortably (worst adjacent pair dE 21.5 protan) but `#ffff00` sits at
1.05 contrast against a light surface. The usual remedy - a white gap between stacked
segments - would make yellow bleed into the background, so segments are separated by a
thin dark edge instead, and the accompanying xlsx serves as the table view that a low
contrast ratio obliges.
"""
import os
import sys

import matplotlib

matplotlib.use('Agg')

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                '..', '..', 'statistics'))

import trajectory_legend as legend  # noqa: E402

# stacking order, innermost (closest to the zero axis) first
GAIN_ORDER = [22, 23, 24, 25, 26]
LOSS_ORDER = [11, 13, 14, 15, 16]

SEGMENT_EDGE = '#3a3a3a'
SEGMENT_EDGE_WIDTH = 0.35

INK = '#1a1a1a'
INK_MUTED = '#6b6b6b'
GRID = '#e2e2e2'

# Both reference lines are black; the dash pattern tells them apart, which survives
# greyscale printing and does not compete with the trajectory colours.
REFERENCE_COLOR = '#000000'

GAIN_STYLE = (0, (6, 2, 1, 2))   # dash-dot
LOSS_STYLE = (0, (1, 2))         # dotted

CLASS_LABELS = {
    'forest_formation': 'Forest Formation',
    'savanna_formation': 'Savanna Formation',
    'wetland': 'Wetland',
    'grassland': 'Grassland',
    'pasture': 'Pasture',
    'agriculture': 'Cropland',
    'urban_area': 'Urban Area',
    'river_lake_and_ocean': 'Water',
}


def _absolute(value, _position):
    """Loss is drawn below zero but labelled as a magnitude."""

    return '{:g}'.format(abs(value))


Y_LABEL = 'Annual change (% of unified size per year)'


def plotTimeIntensity(ax, table, averages=None, title=None, showLegend=False,
                      showYLabel=True, panelLabel=None, sideLabels=True, ylim=None):
    """Draws one class x one territory x one interval grid onto `ax`.

    `table` is the tidy output of time_intensity.buildIntensityTable, already filtered
    to a single (class, territory). `averages` is the matching row of
    time_intensity.averageLines.
    """

    intervals = (table[['year_start', 'year_end', 'duration_years']]
                 .drop_duplicates()
                 .sort_values('year_start'))

    if intervals.empty:
        ax.set_axis_off()
        return ax

    by_key = {}
    for row in table.itertuples():
        value = row.pct_of_unified_per_year
        if value is None or value != value:  # NaN
            value = 0.0
        by_key[(row.year_start, int(row.composite_id))] = float(value)

    centers, widths = [], []
    for interval in intervals.itertuples():
        centers.append((interval.year_start + interval.year_end) / 2.0)
        # exactly the duration: this is what makes bar area equal total change
        widths.append(float(interval.duration_years))

    starts = list(intervals['year_start'])

    for order, sign in ((GAIN_ORDER, 1.0), (LOSS_ORDER, -1.0)):

        bottoms = [0.0] * len(starts)

        for composite in order:
            heights = [sign * by_key.get((start, composite), 0.0) for start in starts]

            if not any(heights):
                continue

            ax.bar(centers, heights, width=widths, bottom=bottoms,
                   align='center',
                   color=legend.TRAJECTORIES[composite % 10]['color'],
                   edgecolor=SEGMENT_EDGE, linewidth=SEGMENT_EDGE_WIDTH,
                   zorder=3)

            bottoms = [b + h for b, h in zip(bottoms, heights)]

    if averages is not None:
        gain = averages.get('gross_gain_pct_per_year')
        loss = averages.get('gross_loss_pct_per_year')

        if gain is not None and gain == gain:
            ax.axhline(float(gain), ls=GAIN_STYLE, lw=1.0,
                       color=REFERENCE_COLOR, zorder=4)
        if loss is not None and loss == loss:
            ax.axhline(-float(loss), ls=LOSS_STYLE, lw=1.1,
                       color=REFERENCE_COLOR, zorder=4)

    ax.axhline(0, color=INK, lw=0.9, zorder=5)

    ax.set_xlim(min(starts), max(intervals['year_end']))
    ax.set_xticks(list(starts) + [max(intervals['year_end'])])
    ax.tick_params(axis='x', labelsize=8, colors=INK_MUTED)
    ax.tick_params(axis='y', labelsize=8, colors=INK_MUTED)

    # Asymmetric limits driven only by the data. The legend sits below the axes, so it
    # needs no headroom and the bars can fill the panel.
    extents = list(_stackExtents(by_key, starts))

    altoGanho = max([g for g, _ in extents] or [0.0])
    altoPerda = max([l for _, l in extents] or [0.0])

    if averages is not None:
        for chave, alvo in (('gross_gain_pct_per_year', 'ganho'),
                            ('gross_loss_pct_per_year', 'perda')):
            valor = averages.get(chave)
            if valor is not None and valor == valor:
                if alvo == 'ganho':
                    altoGanho = max(altoGanho, float(valor))
                else:
                    altoPerda = max(altoPerda, float(valor))

    escala = max(altoGanho, altoPerda, 1e-9)

    if ylim is not None:
        base, topo = ylim
    else:
        topo = max(altoGanho, escala * 0.25) * 1.15
        base = -max(altoPerda, escala * 0.25) * 1.15

    ax.set_ylim(base, topo)
    ax.yaxis.set_major_formatter(FuncFormatter(_absolute))

    ax.set_axisbelow(True)
    for side in ('top', 'right'):
        ax.spines[side].set_visible(False)
    for side in ('left', 'bottom'):
        ax.spines[side].set_color(GRID)

    if sideLabels:
        zero = (0.0 - base) / (topo - base)

        ax.text(-0.065, zero + (1 - zero) * 0.30, 'Gain', transform=ax.transAxes,
                rotation=90, va='center', ha='center', fontsize=8, color=INK_MUTED)
        ax.text(-0.065, zero * 0.55, 'Loss', transform=ax.transAxes,
                rotation=90, va='center', ha='center', fontsize=8, color=INK_MUTED)

    if showYLabel:
        ax.set_ylabel(Y_LABEL, fontsize=9, color=INK_MUTED, labelpad=24)

    if panelLabel:
        ax.text(0.0, 1.02, panelLabel, transform=ax.transAxes, fontsize=10,
                fontweight='bold', color=INK, va='bottom', ha='left')

    if title:
        ax.set_title(title, fontsize=10, color=INK, pad=10)

    if showLegend:
        # Below the axes, never over the data. An inside legend has to be given headroom,
        # and the headroom it needs depends on the class: wetland's axis reaches 12.5%/yr
        # where forest formation's reaches 0.8%/yr.
        ax.legend(handles=legendHandles(), loc='upper center',
                  bbox_to_anchor=(0.5, -0.11), ncol=3, frameon=False,
                  fontsize=7.5, labelspacing=0.35, columnspacing=1.6,
                  handlelength=1.6, handletextpad=0.6, borderaxespad=0.0)

    return ax


def _stackExtents(by_key, starts):
    """(gain total, loss total) per interval, both as positive magnitudes."""

    for start in starts:
        yield (sum(by_key.get((start, c), 0.0) for c in GAIN_ORDER),
               sum(by_key.get((start, c), 0.0) for c in LOSS_ORDER))


def legendHandles():
    """Six trajectory patches plus the two average lines.

    Six, not ten: trajectories 7 and 8 have no changes over the extent, so they can
    carry no annual event and never appear in a bar.
    """

    handles = [
        Patch(facecolor=legend.TRAJECTORIES[t]['color'],
              edgecolor=SEGMENT_EDGE, linewidth=SEGMENT_EDGE_WIDTH,
              label='TR{} - {}'.format(t, legend.TRAJECTORIES[t]['name_en']))
        for t in legend.TRAJECTORIES_WITH_EVENTS
    ]

    handles.append(Line2D([0], [0], ls=GAIN_STYLE, lw=1.0, color=REFERENCE_COLOR,
                          label='Gross gain, 1985-2024 average'))
    handles.append(Line2D([0], [0], ls=LOSS_STYLE, lw=1.1, color=REFERENCE_COLOR,
                          label='Gross loss, 1985-2024 average'))

    return handles


# Two class names differ from the MapBiomas legend. Said once in the caption rather than
# repeated inside two of the eight panel titles, where it would crowd them out.
CLASS_NOTE = ('Cropland is referred to as agriculture in the MapBiomas legend, and water '
              'as river, lakes and oceans.')


def figureCaption(grid):
    """The sentence the figure cannot be read without."""

    return ('Bar width is the interval duration, so bar area is the total change in the '
            'interval; the last interval of the {} grid is shorter. Position above or '
            'below the axis gives gain or loss; colour gives the trajectory over the '
            'whole 1985-2024 extent. {}'.format(grid, CLASS_NOTE))


def saveFigure(fig, path, formats=('png', 'pdf')):
    """Writes the figure in every requested format, creating the folder if needed."""

    folder = os.path.dirname(path)
    if folder and not os.path.isdir(folder):
        os.makedirs(folder)

    written = []
    for extension in formats:
        target = '{}.{}'.format(path, extension)
        fig.savefig(target, dpi=300, bbox_inches='tight', facecolor='white')
        written.append(target)
        print(target)

    plt.close(fig)

    return written


# Components of change (paper, Figure 5): a grey ramp, deliberately outside the
# trajectory palette so the two panels cannot be confused for one another.
COMPONENT_COLORS = {
    'quantity': '#7f7f7f',
    'exchange': '#a8a8a8',
    'alternation': '#d6d6d6',
}

COMPONENT_LABELS = {
    'quantity': 'Quantity',
    'exchange': 'Exchange',
    'alternation': 'Alternation',
}


def plotComponents(ax, row, title=None, showLegend=True, panelLabel=None, ylim=None):
    """Draws the single stacked bar of Quantity, Exchange and Alternation.

    `row` is one record of time_intensity.componentsOfChange. Stacking order follows the
    paper: Quantity at the bottom, then Exchange, then Alternation.
    """

    bottom = 0.0
    handles = []

    for key in ('quantity', 'exchange', 'alternation'):
        height = float(row['{}_pct_per_year'.format(key)])

        ax.bar([0], [height], width=0.46, bottom=[bottom],
               color=COMPONENT_COLORS[key], edgecolor=SEGMENT_EDGE,
               linewidth=SEGMENT_EDGE_WIDTH, zorder=3)

        label = COMPONENT_LABELS[key]

        if key == 'quantity':
            # the legend names which side the net change fell on, as the paper does
            label = 'Quantity {}'.format(str(row.get('quantity_direction', '')).title())

        handles.append(Patch(facecolor=COMPONENT_COLORS[key], edgecolor=SEGMENT_EDGE,
                             linewidth=SEGMENT_EDGE_WIDTH, label=label))

        bottom += height

    ax.set_xlim(-0.5, 0.5)
    ax.set_xticks([])
    ax.set_ylim(*(ylim if ylim is not None
                  else (0, bottom * 1.08 if bottom else 1.0)))
    ax.tick_params(axis='y', labelsize=8, colors=INK_MUTED)
    ax.set_axisbelow(True)

    for side in ('top', 'right'):
        ax.spines[side].set_visible(False)
    for side in ('left', 'bottom'):
        ax.spines[side].set_color(GRID)

    direcao = str(row.get('quantity_direction', '') or '').lower()

    # One line, not two: a second line reaches down into the title of the row below
    ax.set_xlabel('All intervals' if not direcao
                  else 'All intervals, net {}'.format(direcao),
                  fontsize=8, color=INK_MUTED)

    if panelLabel:
        ax.text(0.0, 1.02, panelLabel, transform=ax.transAxes, fontsize=10,
                fontweight='bold', color=INK, va='bottom', ha='left')

    if title:
        ax.set_title(title, fontsize=9, color=INK, pad=10)

    if showLegend:
        # same convention as panel (a): below the axes
        ax.legend(handles=handles[::-1], loc='upper center',
                  bbox_to_anchor=(0.5, -0.11), ncol=1, frameon=False,
                  fontsize=7.5, labelspacing=0.35, handlelength=1.6,
                  handletextpad=0.6, borderaxespad=0.0)

    return ax


# ---------------------------------------------------------------------------
# Paper style and the complete figure
# ---------------------------------------------------------------------------

# The paper sets its figures in Palatino Linotype at 10 pt, black. "Palatino Linotype" is
# the Microsoft name; macOS ships the same face as "Palatino" and Linux distributions as
# "P052" or "URW Palladio L". The chain covers all three and falls back to a generic
# serif, so the figures render sensibly wherever they are built.
PAPER_FONTS = ['Palatino Linotype', 'Palatino', 'P052', 'URW Palladio L',
               'Book Antiqua', 'serif']

PAPER_SIZE = 10


def usePaperStyle(size=PAPER_SIZE):
    """Switches the module to the paper's typography: Palatino, 10 pt, black.

    Rebinds the ink constants as well, because several marks pass an explicit colour
    rather than relying on rcParams.
    """
    global INK, INK_MUTED, GRID

    INK = '#000000'
    INK_MUTED = '#000000'
    GRID = '#cccccc'

    matplotlib.rcParams.update({
        'font.family': 'serif',
        'font.serif': PAPER_FONTS,
        'font.size': size,
        'axes.labelsize': size,
        'axes.titlesize': size,
        'xtick.labelsize': size - 1,
        'ytick.labelsize': size - 1,
        'legend.fontsize': size - 1,
        'figure.titlesize': size + 1,
        'text.color': '#000000',
        'axes.labelcolor': '#000000',
        'axes.edgecolor': '#000000',
        'xtick.color': '#000000',
        'ytick.color': '#000000',
        'axes.titlecolor': '#000000',
        'pdf.fonttype': 42,      # embed TrueType so the PDF keeps the face
        'ps.fonttype': 42,
    })


def panelLetters(count, start=0):
    """(a), (b), (c) ... for `count` panels, as journals label them."""

    return ['({})'.format(chr(ord('a') + start + i)) for i in range(count)]


def plotCompleteFigure(table, components, averages, classOrder, territory, gridLabel,
                       classLabels=None, columns=2):
    """One figure with every class: a grid of cells, each holding panels (a) and (b).

    Laid out `columns` wide and as many rows as it takes - with 8 classes and 2 columns,
    4 rows. Each cell pairs the change-per-interval chart with its components bar, and
    the whole figure carries one legend at the foot rather than one per panel.
    """

    classLabels = classLabels or CLASS_LABELS

    rows = -(-len(classOrder) // columns)

    fig = plt.figure(figsize=(6.6 * columns, 3.0 * rows + 1.9))

    larguras = []
    for _ in range(columns):
        larguras += [3.0, 0.85]

    malha = fig.add_gridspec(rows, 2 * columns, width_ratios=larguras,
                             hspace=0.55, wspace=0.42)

    letras = panelLetters(2 * len(classOrder))

    for indice, className in enumerate(classOrder):
        linha, coluna = divmod(indice, columns)

        eixoTempo = fig.add_subplot(malha[linha, 2 * coluna])
        eixoComponentes = fig.add_subplot(malha[linha, 2 * coluna + 1])

        linhas = table[table['class_name'] == className]

        media = averages[averages['class_name'] == className]
        parte = components[components['class_name'] == className]

        plotTimeIntensity(
            eixoTempo, linhas,
            media.iloc[0] if len(media) else None,
            title=classLabels.get(className, className),
            panelLabel=letras[2 * indice])

        if len(parte) and not linhas.empty:
            plotComponents(eixoComponentes, parte.iloc[0],
                           showLegend=False, panelLabel=letras[2 * indice + 1])
        else:
            eixoComponentes.set_axis_off()

    fig.suptitle('{} — {} intervals'.format(territory, gridLabel), y=0.985)

    fig.legend(handles=legendHandles() + componentHandles(),
               loc='lower center', ncol=4, frameon=False,
               bbox_to_anchor=(0.5, 0.032))

    fig.text(0.5, 0.012, figureCaption(gridLabel), fontsize=PAPER_SIZE - 2,
             color=INK_MUTED, ha='center')

    fig.subplots_adjust(left=0.055, right=0.985, top=0.945, bottom=0.115)

    return fig


def componentHandles():
    """Legend entries for the three components, for the shared footer legend."""

    return [Patch(facecolor=COMPONENT_COLORS[key], edgecolor=SEGMENT_EDGE,
                  linewidth=SEGMENT_EDGE_WIDTH, label=COMPONENT_LABELS[key])
            for key in ('quantity', 'exchange', 'alternation')]


# Height of the one-axes components figure. Half a page: it holds eight columns and a
# three-entry legend, and nothing else.
COMPONENTS_BAR_HEIGHT = 3.45

# Letter printed over each column for the side the Quantity component falls on. One
# character, because the words do not fit eight times across a single axis.
DIRECTION_MARK = {'loss': 'L', 'gain': 'G'}


def plotComponentsByClass(ax, components, classOrder, classLabels=None, ylim=None,
                          markDirection=True, barWidth=0.62, rotation=35):
    """Every class as one column of a single stacked bar chart.

    The eight panels of `plotClassGrid('components', ...)` answer "what is this class's
    change made of". This answers "which class changes fastest, and of what" - the
    comparison the unified-size denominator exists to make possible, since it puts a class
    covering half the country on the same axis as one covering 0.5% of it.

    `markDirection` prints L or G over each column for the side the Quantity component
    falls on. It replaces the per-panel "All intervals, net loss" label, which cannot be
    repeated eight times across one axis without crowding it; the caption explains the
    letter.
    """

    classLabels = classLabels or CLASS_LABELS

    posicoes = []
    rotulos = []
    topo = 0.0

    for indice, className in enumerate(classOrder):
        linhas = components[components['class_name'] == className]

        posicoes.append(indice)
        rotulos.append(classLabels.get(className, className))

        if linhas.empty:
            continue

        row = linhas.iloc[0]

        bottom = 0.0

        for key in ('quantity', 'exchange', 'alternation'):
            height = float(row['{}_pct_per_year'.format(key)])

            ax.bar([indice], [height], width=barWidth, bottom=[bottom],
                   color=COMPONENT_COLORS[key], edgecolor=SEGMENT_EDGE,
                   linewidth=SEGMENT_EDGE_WIDTH, zorder=3)

            bottom += height

        topo = max(topo, bottom)

        if markDirection:
            marca = DIRECTION_MARK.get(
                str(row.get('quantity_direction', '') or '').lower())

            if marca:
                ax.text(indice, bottom, marca, ha='center', va='bottom',
                        fontsize=PAPER_SIZE - 2, color=INK, zorder=4)

    # Headroom for the direction letters, which sit on top of the tallest column.
    ax.set_ylim(*(ylim if ylim is not None
                  else (0, topo * 1.12 if topo else 1.0)))

    ax.set_xlim(-0.7, len(classOrder) - 0.3)
    ax.set_xticks(posicoes)
    ax.set_xticklabels(rotulos, rotation=rotation, ha='right',
                       fontsize=PAPER_SIZE - 2, color=INK)

    ax.tick_params(axis='y', labelsize=PAPER_SIZE - 2, colors=INK_MUTED)
    ax.set_axisbelow(True)

    for side in ('top', 'right'):
        ax.spines[side].set_visible(False)
    for side in ('left', 'bottom'):
        ax.spines[side].set_color(GRID)

    return ax


def componentsByClassFigure(components, classOrder, classLabels=None, figsize=None,
                            ylim=None):
    """The one-axes components figure, legend at the foot as in the grid figures."""

    figsize = figsize or (A4_WIDTH, COMPONENTS_BAR_HEIGHT)

    fig = plt.figure(figsize=figsize)

    ax = fig.add_subplot(1, 1, 1)

    plotComponentsByClass(ax, components, classOrder, classLabels=classLabels,
                          ylim=ylim)

    ax.set_ylabel('Annual change (% of unified size per year)',
                  fontsize=PAPER_SIZE - 1, color=INK, labelpad=6)

    fig.legend(handles=componentHandles(), loc='lower center', ncol=3, frameon=False,
               fontsize=PAPER_SIZE - 3.5, labelspacing=0.4, columnspacing=1.4,
               handlelength=1.5, handletextpad=0.5, borderaxespad=0.0,
               bbox_to_anchor=(0.5, 0.008))

    fig.subplots_adjust(left=0.125, right=0.975, top=0.965, bottom=0.30)

    return fig


def componentsByClassCaption(territory=None, classCount=8):
    """Caption for the one-axes components figure, as running text."""

    onde = ' in {}'.format(territory) if territory else ''

    return (
        'Components of change of {} land cover classes{}, 1985-2024. Each column is one '
        'class. The vertical axis is the total gross change over the temporal extent, '
        'annualised and expressed as a percentage of that class unified size, the union '
        'of where the class occurs at any time point; because each class is divided by '
        'its own unified size, the columns are directly comparable although the classes '
        'differ in area by two orders of magnitude. Each column is split into three '
        'components: Quantity, the net change between the first and last time point; '
        'Exchange, gain at some locations paired with loss at others between those same '
        'two points; and Alternation, gain and loss at one location through the series, '
        'which a comparison of two time points cannot detect. The letter above each '
        'column is the direction of the net change that the Quantity component measures: '
        'L for net loss, G for net gain. All intervals of the temporal extent are '
        'included, so the figure does not depend on the choice of interval grid.'
        ' {}'.format(classCount, onde, CLASS_NOTE))


# A4 is 210 x 297 mm; with the margins a journal leaves, a full-page figure is about
# 170 x 230 mm. In inches, that is the ceiling both grid figures are built to.
A4_WIDTH = 6.45
A4_HEIGHT = 8.8

# Vertical gap between rows of panels, as a fraction of the panel height. It has to clear
# whatever hangs below the row above - tick labels in the coloured figure, the x label in
# the grey one - and the title of the row below. Per figure type, because the two have
# different things hanging there. selftest_pipeline.rowClearance measures what is left; it
# can go negative, and the collision is invisible in a thumbnail.
ROW_SPACING = {'trajectories': 0.40, 'components': 0.62}


def plotClassGrid(kind, table, components, averages, classOrder, territory, gridLabel,
                  classLabels=None, columns=2, figsize=None, compactTicks=True,
                  hspace=None, wspace=0.34, sharedY=False):
    """One figure holding every class, in a `columns`-wide grid.

    `kind` picks which chart fills each cell: 'trajectories' for the coloured
    change-per-interval chart, 'components' for the grey decomposition. They are separate
    figures rather than one, because the pair does not fit an A4 page at a legible size.

    Cell positions match between the two figures, so panel (c) of one is the same class as
    panel (c) of the other.
    """

    classLabels = classLabels or CLASS_LABELS

    rows = -(-len(classOrder) // columns)

    if figsize is None:
        altura = A4_HEIGHT if kind == 'trajectories' else A4_HEIGHT * 0.80
        figsize = (A4_WIDTH, altura)

    fig = plt.figure(figsize=figsize)

    if hspace is None:
        hspace = ROW_SPACING[kind]

    malha = fig.add_gridspec(rows, columns, hspace=hspace, wspace=wspace)

    limites = (sharedLimits(kind, table, components, classOrder)
               if sharedY else None)

    letras = panelLetters(len(classOrder))

    for indice, className in enumerate(classOrder):
        linha, coluna = divmod(indice, columns)

        ax = fig.add_subplot(malha[linha, coluna])

        linhas = table[table['class_name'] == className]
        media = averages[averages['class_name'] == className]
        parte = components[components['class_name'] == className]

        titulo = classLabels.get(className, className)

        if kind == 'trajectories':
            # one shared y label for the figure, not eight competing for the margin
            plotTimeIntensity(ax, linhas,
                              media.iloc[0] if len(media) else None,
                              title=titulo, panelLabel=letras[indice],
                              showYLabel=False, sideLabels=False, ylim=limites)

            if compactTicks:
                _thinTicks(ax)
        else:
            if len(parte) and not linhas.empty:
                plotComponents(ax, parte.iloc[0], title=titulo,
                               showLegend=False, panelLabel=letras[indice],
                               ylim=limites)
            else:
                ax.set_axis_off()

    # Plain label. Gain and loss are read from the side of the zero axis, which the
    # caption states; crowding the words against the label read as an accident.
    fig.supylabel('Annual change (% of unified size per year)',
                  fontsize=PAPER_SIZE - 1, x=0.055)

    if kind == 'trajectories':
        handles, ncol, rodape = legendHandles(), 4, 0.115
    else:
        handles, ncol, rodape = componentHandles(), 3, 0.170

    # Sized to fit inside the figure width: bbox_inches='tight' would otherwise widen
    # the saved image to the legend and push it past the A4 text block.
    fig.legend(handles=handles, loc='lower center', ncol=ncol, frameon=False,
               fontsize=PAPER_SIZE - 3.5, labelspacing=0.4, columnspacing=1.0,
               handlelength=1.5, handletextpad=0.5, borderaxespad=0.0,
               bbox_to_anchor=(0.5, 0.012))

    # The caption is not drawn on the figure: it is set as running text by the journal,
    # so the runner writes it to captions.txt instead.
    fig.subplots_adjust(left=0.125, right=0.925, top=0.965, bottom=rodape)

    return fig


def sharedLimits(kind, table, components, classOrder):
    """Y limits wide enough for every class in `classOrder`.

    A shared axis answers a different question from a free one: not "how did this class
    change over time" but "which class changes more". It costs the small classes their
    detail - urban area's axis is 1.7%/yr against wetland's 10.6 - which is why both
    versions are produced rather than one replacing the other.
    """

    if kind == 'components':
        alturas = [row['quantity_pct_per_year'] + row['exchange_pct_per_year']
                   + row['alternation_pct_per_year']
                   for _, row in components.iterrows()
                   if row['class_name'] in classOrder]

        return (0, max(alturas) * 1.08) if alturas else None

    ganho = perda = 0.0

    for className in classOrder:
        linhas = table[table['class_name'] == className]

        for _, grupo in linhas.groupby('year_start'):
            somas = grupo.groupby('event')['pct_of_unified_per_year'].sum()
            ganho = max(ganho, float(somas.get('gain', 0.0) or 0.0))
            perda = max(perda, float(somas.get('loss', 0.0) or 0.0))

    if not (ganho or perda):
        return None

    return (-perda * 1.15, ganho * 1.15)


def _thinTicks(ax, keep=2):
    """Shows every `keep`-th x tick label, so the years stay legible at A4 width."""

    rotulos = ax.get_xticklabels()

    for indice, rotulo in enumerate(rotulos):
        if indice % keep and indice != len(rotulos) - 1:
            rotulo.set_visible(False)


def captionFor(kind, gridLabel, territory=None, classCount=8, sharedY=False):
    """The caption for a grid figure, as running text for the publication.

    Self-contained on purpose: the figures carry no title, so the caption has to name the
    territory, the interval grid, which vertical scale is in use and what each panel shows.
    """

    onde = ' in {}'.format(territory) if territory else ''

    ultima = chr(ord('a') + classCount - 1)

    if sharedY:
        escala = (' All panels share one vertical scale, so the classes are directly '
                  'comparable; the smaller ones therefore occupy little of their panel.')
    else:
        escala = (' Each panel has its own vertical scale, chosen to fill it: compare the '
                  'shape within a panel, not the height between panels.')

    if kind == 'trajectories':
        return (
            'Annual change of {} land cover classes{}, {} intervals, 1985-2024. Each '
            'panel is one class, labelled (a) to ({}). The vertical axis is the annual '
            'gross change as a percentage of the class unified size, the union of where '
            'the class occurs at any time point. Gains rise above the time axis and '
            'losses fall below it. Colours within a stacked bar give the pixel trajectory '
            'over the whole 1985-2024 extent, so the same colour means the same thing in '
            'every bar and a trajectory that alternates appears on both sides. The '
            'vertical length from the top of the gain to the bottom of the loss is the '
            'speed of change in that interval. Bar width is the interval duration, so the '
            'area of each bar is the amount of change during the interval; the last '
            'interval of the {} grid is shorter than the others. The dashed lines are the '
            'gross gain and gross loss averaged over the temporal extent.{} {}'.format(
                classCount, onde, gridLabel, ultima, gridLabel, escala, CLASS_NOTE))

    return (
        'Components of change of {} land cover classes{}, 1985-2024. Each panel is one '
        'class, labelled (a) to ({}), in the same position as in the companion figure of '
        'annual change. Each bar is the total gross change over the temporal extent, '
        'annualised and expressed as a percentage of the class unified size, split into '
        'three components: Quantity, the net change between the first and last time '
        'point; Exchange, gain at some locations paired with loss at others between those '
        'same two points; and Alternation, gain and loss at one location through the '
        'series, which a comparison of two time points cannot detect. The direction of '
        'the net change is printed under each bar.{} {}'.format(
            classCount, onde, ultima, escala, CLASS_NOTE))


def componentsCaption():
    """The sentence the grey figure cannot be read without."""

    return ('Each bar is the total gross change over 1985-2024, annualised and expressed '
            'as a percentage of the class unified size, split into the net change '
            '(Quantity), the part exchanged between locations, and the part reversed at '
            'one location (Alternation). The direction of the net change is printed under '
            'each bar. ' + CLASS_NOTE)
