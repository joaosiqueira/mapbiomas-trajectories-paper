"""Turns the exported time-intensity GeoJSON into the table the figures are drawn from.

The exported rows carry a CLASSE value that says what they are:

    1..8    area per base trajectory over 1985-2024  (property grid == 'base')
            -> the denominator, the class's "unified size"
    11..16  area LOST during the interval, by base trajectory
    22..26  area GAINED during the interval, by base trajectory

The metric on the vertical axis is annual gross change as a percentage of the unified
size:

    annual_area  = gross_area / duration_years
    pct_per_year = 100 * annual_area / unified_size

`gross_area` counts a pixel once per transition, so a pixel that flips twice inside an
interval is counted twice. It is a quantity of change, not an area of land - hence the
column name `gross change (hectare)`.
"""
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                '..', '..', 'statistics'))

import config  # noqa: E402
import trajectory_legend as legend  # noqa: E402

# what tables.loadFiles writes
SOURCE_AREA_COLUMN = 'area (hectare)'

# what we call it downstream: a pixel that flips twice in an interval is counted twice,
# so the number is a quantity of change, not an area of land
AREA_COLUMN = 'gross change (hectare)'

GROUP_COLUMNS = ['category', 'feature_id', 'class_id', 'class_name']


def prepare(df):
    """Renames the loaded area column and drops rows the figure cannot use."""

    df = df.copy()

    if SOURCE_AREA_COLUMN in df.columns and AREA_COLUMN not in df.columns:
        df = df.rename(columns={SOURCE_AREA_COLUMN: AREA_COLUMN})

    if 'grid' not in df.columns:
        raise ValueError(
            "no 'grid' column: load with extraProperties=('grid',)")

    return df


def splitComposite(df):
    """Adds event_id / trajectory_id / labels / colour from the composite id."""

    df = df.copy()

    df['event_id'] = df['composite_id'] // 10
    df['trajectory_id'] = df['composite_id'] % 10

    df['event'] = df['event_id'].map(
        {legend.LOSS: 'loss', legend.GAIN: 'gain'})

    df['trajectory_label_en'] = df['trajectory_id'].map(
        {key: value['name_en'] for key, value in legend.TRAJECTORIES.items()})

    df['trajectory_path'] = df['trajectory_id'].map(
        {key: value['path_en'] for key, value in legend.TRAJECTORIES.items()})

    df['color'] = df['trajectory_id'].map(
        {key: value['color'] for key, value in legend.TRAJECTORIES.items()})

    return df


def addIntervalColumns(df):
    """Splits the `period` label into start, end and duration."""

    df = df.copy()

    years = df['period'].str.split('-', expand=True).astype(int)

    df['year_start'] = years[0]
    df['year_end'] = years[1]
    df['duration_years'] = df['year_end'] - df['year_start']

    return df


# Share of gross change that may sit in impossible composites before we stop trusting
# the data. Anything above this is a real disagreement between the events and the base.
INVALID_TOLERANCE = 0.005


def checkComposites(df, tolerance=INVALID_TOLERANCE):
    """Finds composites that cannot physically occur and decides whether to tolerate them.

    Two different things produce them.

    A pixel whose time series has masked years gets base trajectory 0: the `.where()`
    chain leaves its default because the conditions are masked, while transitions between
    two unmasked years still register an event. That yields composite 10 or 20. These are
    edge pixels - the Brazil border, gaps in the series - and in collection 10 they are
    about 0.01% of all gross change, so they are reported and dropped.

    A real disagreement between the class definition behind the events and the one behind
    the base trajectory would also produce impossible composites, but in bulk. That is
    what the tolerance separates: below it, edge pixels; above it, a broken pipeline.

    Returns the set of composite ids to drop.
    """

    observed = set(int(value) for value in df['composite_id'].unique())

    invalid = observed - set(legend.COMPOSITES)

    if not invalid:
        return set()

    total = df[AREA_COLUMN].sum()
    lost = df[df['composite_id'].isin(invalid)][AREA_COLUMN].sum()
    share = lost / total if total else 0.0

    if share > tolerance:
        raise ValueError(
            'impossible composites {} hold {:.2%} of the gross change, above the {:.2%} '
            'tolerance. The annual events and the base trajectory were probably built '
            'from different class definitions.'.format(
                sorted(invalid), share, tolerance))

    print('  dropping composites {} ({:.4f}% of gross change, {:.0f} ha): pixels whose '
          'series has masked years, so they have no base trajectory'.format(
              sorted(invalid), 100 * share, lost))

    return invalid


def unifiedSize(df):
    """The denominator per class and territory: the union over the whole extent.

    Base trajectory 8 is "absent in every year", so it is excluded.
    """

    base = df[df['grid'] == 'base']

    if base.empty:
        raise ValueError('no grid == "base" rows; the denominator is missing')

    present = base[base['composite_id'].isin(legend.UNIFIED_SIZE_TRAJECTORIES)]

    unified = present.groupby(GROUP_COLUMNS, as_index=False)[AREA_COLUMN].sum()

    return unified.rename(columns={AREA_COLUMN: 'unified_size_ha'})


def buildIntensityTable(df, grid):
    """The tidy table for one interval grid: one row per interval x composite."""

    unified = unifiedSize(df)

    events = df[df['grid'] == grid].copy()

    if events.empty:
        raise ValueError('no rows for grid {}'.format(grid))

    descartar = checkComposites(events)

    if descartar:
        events = events[~events['composite_id'].isin(descartar)]

    events = addIntervalColumns(splitComposite(events))

    keys = GROUP_COLUMNS + ['grid', 'period', 'year_start', 'year_end',
                            'duration_years', 'composite_id', 'event_id', 'event',
                            'trajectory_id', 'trajectory_label_en', 'trajectory_path',
                            'color']

    table = events.groupby(keys, as_index=False)[AREA_COLUMN].sum()

    table = table.merge(unified, on=GROUP_COLUMNS, how='left')

    table['annual_area_ha_per_year'] = table[AREA_COLUMN] / table['duration_years']

    # a class absent from a territory has unified_size 0; leave it as NaN, not inf
    table['pct_of_unified_per_year'] = pd.NA
    valid = table['unified_size_ha'] > 0
    table.loc[valid, 'pct_of_unified_per_year'] = (
        100.0 * table.loc[valid, 'annual_area_ha_per_year']
        / table.loc[valid, 'unified_size_ha'])

    table['pct_signed'] = table['pct_of_unified_per_year'].where(
        table['event_id'] == legend.GAIN,
        -table['pct_of_unified_per_year'])

    return table.sort_values(GROUP_COLUMNS + ['year_start', 'event_id',
                                              'trajectory_id']).reset_index(drop=True)


def averageLines(df):
    """The two dashed lines: gross gain and gross loss averaged over the extent.

    Computed from the base grid, so the value does not depend on which grid is plotted.
    """

    unified = unifiedSize(df)

    events = df[df['grid'] != 'base'].copy()

    # every grid tiles the same 39 transitions, so use one of them to avoid double count
    grid = sorted(set(events['grid']))[0]
    events = events[events['grid'] == grid]

    # same drop as buildIntensityTable, or the dashed lines would not match the bars
    events = events[events['composite_id'].isin(legend.COMPOSITES)]

    events = splitComposite(events)

    totals = events.groupby(GROUP_COLUMNS + ['event'], as_index=False)[AREA_COLUMN].sum()

    totals = totals.pivot_table(index=GROUP_COLUMNS, columns='event',
                                values=AREA_COLUMN, fill_value=0.0).reset_index()

    for column in ('gain', 'loss'):
        if column not in totals.columns:
            totals[column] = 0.0

    totals = totals.merge(unified, on=GROUP_COLUMNS, how='left')

    valid = totals['unified_size_ha'] > 0

    for name, column in (('gain', 'gross_gain_pct_per_year'),
                         ('loss', 'gross_loss_pct_per_year')):
        totals[column] = pd.NA
        totals.loc[valid, column] = (
            100.0 * totals.loc[valid, name] / config.N_TRANSITIONS
            / totals.loc[valid, 'unified_size_ha'])

    totals['total_change_pct_per_year'] = (
        totals['gross_gain_pct_per_year'] + totals['gross_loss_pct_per_year'])
    totals['net_change_pct_per_year'] = (
        totals['gross_gain_pct_per_year'] - totals['gross_loss_pct_per_year'])

    return totals.rename(columns={'gain': 'gross_gain_ha', 'loss': 'gross_loss_ha'})


def legendTable():
    """The reconstructed composite legend, as a dataframe for the xlsx."""

    return pd.DataFrame(legend.legend_rows())


# ---------------------------------------------------------------------------
# Components of change, Bilintoh, Pontius & Zhang (2024) equations 6 to 9.
# This is the companion decomposition to the stacked-bar figure: the same total
# gross change, split by *why* it happened instead of by trajectory.
# ---------------------------------------------------------------------------

# Trajectories whose endpoints differ, so they carry net change (paper, Table 2):
#   1 and 3 go presence -> absence, so Y_T - Y_0 = -1
#   2 and 4 go absence -> presence, so Y_T - Y_0 = +1
ENDPOINT_LOSS_TRAJECTORIES = [1, 3]
ENDPOINT_GAIN_TRAJECTORIES = [2, 4]


def componentsOfChange(df):
    """Quantity, Exchange and Alternation per territory and class, in % per year.

    Equations 7 to 9 of the paper. Because trajectories 1 to 4 have known endpoints,
    the sums over cells reduce to areas we already exported:

        Quantity    = |A2 + A4 - A1 - A3| / (U * D)          (eq 7)
        Exchange    = (A1 + A2 + A3 + A4) / (U * D) - Quantity   (eq 8)
        Alternation = Gain - Loss - Exchange - Quantity       (eq 9)

    where A(j) is the area of trajectory j over the whole extent, U is the unified size
    and D the temporal extent in years. Quantity is the net change between the first and
    last time point; Exchange is gain in one place paired with loss in another between
    those same two points; Alternation is the gain/loss pairs at one place through the
    series - the part that endpoint comparison cannot see.

    The three sum to the total gross change, which `checkComponents` verifies.
    """

    base = df[df['grid'] == 'base']

    if base.empty:
        raise ValueError('no grid == "base" rows; the trajectory areas are missing')

    areas = (base.groupby(GROUP_COLUMNS + ['composite_id'], as_index=False)[AREA_COLUMN]
             .sum()
             .rename(columns={'composite_id': 'trajectory_id'}))

    unified = unifiedSize(df)

    def total(frame, ids):
        rows = frame[frame['trajectory_id'].isin(ids)]
        return rows.groupby(GROUP_COLUMNS)[AREA_COLUMN].sum()

    perdaFim = total(areas, ENDPOINT_LOSS_TRAJECTORIES)
    ganhoFim = total(areas, ENDPOINT_GAIN_TRAJECTORIES)

    out = unified.set_index(GROUP_COLUMNS).copy()
    out['endpoint_loss_ha'] = perdaFim.reindex(out.index).fillna(0.0)
    out['endpoint_gain_ha'] = ganhoFim.reindex(out.index).fillna(0.0)

    escala = out['unified_size_ha'] * config.N_TRANSITIONS

    liquido = out['endpoint_gain_ha'] - out['endpoint_loss_ha']

    out['quantity_pct_per_year'] = 100.0 * liquido.abs() / escala
    out['exchange_pct_per_year'] = (
        100.0 * (out['endpoint_gain_ha'] + out['endpoint_loss_ha']) / escala
        - out['quantity_pct_per_year'])

    # which side the quantity component sits on, for the legend (paper, Figure 5)
    out['quantity_direction'] = ['gain' if v > 0 else 'loss' for v in liquido]

    medias = averageLines(df).set_index(GROUP_COLUMNS)

    out['gross_gain_pct_per_year'] = medias['gross_gain_pct_per_year'].reindex(out.index)
    out['gross_loss_pct_per_year'] = medias['gross_loss_pct_per_year'].reindex(out.index)

    out['total_change_pct_per_year'] = (
        out['gross_gain_pct_per_year'] + out['gross_loss_pct_per_year'])

    out['alternation_pct_per_year'] = (
        out['total_change_pct_per_year']
        - out['exchange_pct_per_year']
        - out['quantity_pct_per_year'])

    return out.reset_index()


def checkComponents(components, tolerance=1e-9):
    """The three components must add up to the total gross change (equation 9)."""

    soma = (components['quantity_pct_per_year']
            + components['exchange_pct_per_year']
            + components['alternation_pct_per_year'])

    erro = (soma - components['total_change_pct_per_year']).abs().max()

    if erro > tolerance:
        raise ValueError(
            'components do not close: worst gap {:.3e} percentage points'.format(erro))

    negativas = components[components['alternation_pct_per_year'] < -tolerance]

    if len(negativas):
        raise ValueError(
            'negative Alternation for {} rows, which is impossible: {}'.format(
                len(negativas),
                negativas[GROUP_COLUMNS].head(3).to_dict('records')))

    return erro
