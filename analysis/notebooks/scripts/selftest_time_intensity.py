"""Proves the invariants the time-intensity figures rest on. Needs no GEE credentials.

Run: python selftest_time_intensity.py

The interesting part is test 1. The claim that exactly 10 composites can occur is not a
convention to be trusted, it is a property of the classifier, so it is proven here by
enumerating every possible presence series. The classifier below is a deliberate
transcription of the `.where()` chain in
statistics/annual_events.py; if that chain is ever edited and this
transcription is not, these tests are what notices.
"""
import io
import os
import re
import sys
from itertools import product

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                '..', '..', 'statistics'))

import config  # noqa: E402
import trajectory_legend as legend  # noqa: E402

# read from config.py rather than restated here, so the two cannot drift apart
YEARS = config.YEARS
INTERVAL_GRIDS = config.INTERVAL_GRIDS
N_TRANSITIONS = config.N_TRANSITIONS


def number_of_changes(presence):
    """ee.Reducer.countRuns() - 1 over the binary presence mask."""

    runs = 1
    for previous, current in zip(presence, presence[1:]):
        if previous != current:
            runs += 1

    return runs - 1


def base_trajectory(presence):
    """Transcription of the .where() chain, applied in the same order (later wins)."""

    changes = number_of_changes(presence)
    first, last = presence[0], presence[-1]

    eq0, eq1, gt1 = changes == 0, changes == 1, changes > 1

    value = 0
    if first == 1 and eq1 and last == 0: value = 1
    if first == 0 and eq1 and last == 1: value = 2
    if first == 1 and gt1 and last == 0: value = 3
    if first == 0 and gt1 and last == 1: value = 4
    if first == 1 and gt1 and last == 1: value = 5
    if first == 0 and gt1 and last == 0: value = 6
    if first == 1 and eq0:               value = 7
    if first == 0 and eq0:               value = 8

    return value


def annual_events(presence):
    """Per-transition event: 1 = loss, 2 = gain, 0 = no change."""

    events = []
    for previous, current in zip(presence, presence[1:]):
        if previous == 1 and current == 0:
            events.append(legend.LOSS)
        elif previous == 0 and current == 1:
            events.append(legend.GAIN)
        else:
            events.append(0)

    return events


def test_composite_rule():
    """Exhaustive: only the 10 composites occur, and the impossible ones never do."""

    observed = set()
    checked = 0

    for length in range(2, 17):
        for presence in product([0, 1], repeat=length):
            base = base_trajectory(presence)
            events = annual_events(presence)

            assert base != 0, 'unclassified presence series {}'.format(presence)

            # every change is an event, and every event is a change
            assert sum(1 for e in events if e) == number_of_changes(presence)

            # gross loss minus gross gain is the net drop in presence
            losses = sum(1 for e in events if e == legend.LOSS)
            gains = sum(1 for e in events if e == legend.GAIN)
            assert losses - gains == presence[0] - presence[-1]

            for event in events:
                if event:
                    observed.add(event * 10 + base)

            checked += 1

    assert observed == set(legend.COMPOSITES), (
        'observed {} != legend {}'.format(sorted(observed), sorted(legend.COMPOSITES)))

    impossible = {e * 10 + b for e in (legend.LOSS, legend.GAIN) for b in range(1, 9)} - observed
    assert impossible == {12, 17, 18, 21, 27, 28}, sorted(impossible)

    for composite in observed:
        assert legend.is_valid_composite(composite)
        legend.describe(composite)

    for trajectory_id in (7, 8):
        assert trajectory_id not in {c % 10 for c in observed}, (
            'trajectory {} has no changes so it can carry no event'.format(trajectory_id))

    print('  1. regra dos compostos  OK  (%d series testadas, %d compostos: %s)'
          % (checked, len(observed), sorted(observed)))


def test_interval_grids():
    """Each grid tiles the 39 transitions exactly: no gap, no overlap."""

    transitions = [(year, year + 1) for year in YEARS[:-1]]

    assert len(transitions) == N_TRANSITIONS

    for name, intervals in INTERVAL_GRIDS.items():
        assigned = {}

        for start, end in intervals:
            assert end > start, (name, start, end)
            for year in range(start, end):
                key = (year, year + 1)
                assert key not in assigned, 'overlap at {} in grid {}'.format(key, name)
                assigned[key] = (start, end)

        missing = [t for t in transitions if t not in assigned]
        assert not missing, 'grid {} misses {}'.format(name, missing)

        durations = [end - start for start, end in intervals]
        assert sum(durations) == N_TRANSITIONS, (name, sum(durations))

        boundaries = [intervals[0][0]] + [end for _, end in intervals]
        assert boundaries == sorted(boundaries), name
        assert boundaries[0] == YEARS[0] and boundaries[-1] == YEARS[-1], name

        print('  2. grade %-4s           OK  (%d intervalos, larguras %s, soma %d)'
              % (name, len(intervals), durations, sum(durations)))


def test_grid_equivalence():
    """Both grids cover the same transitions, so per-composite totals must agree.

    This is the strongest end-to-end check available without GEE: it is what catches a
    mis-assigned interval in the aggregation step.
    """

    # synthetic per-transition areas, arbitrary but fixed
    areas = {}
    for index, year in enumerate(YEARS[:-1]):
        for composite in legend.COMPOSITES:
            areas[(year, composite)] = (index + 1) * (composite % 10) * 1.5

    def total_by_grid(intervals):
        totals = {}
        for start, end in intervals:
            for year in range(start, end):
                for composite in legend.COMPOSITES:
                    totals[composite] = totals.get(composite, 0.0) + areas[(year, composite)]
        return totals

    five = total_by_grid(INTERVAL_GRIDS['5y'])
    ten = total_by_grid(INTERVAL_GRIDS['10y'])

    assert five.keys() == ten.keys()
    for composite in five:
        assert abs(five[composite] - ten[composite]) < 1e-9, composite

    print('  3. equivalencia 5y/10y  OK  (%d compostos batem)' % len(five))


def test_area_identity():
    """sum(width x height) over the bars equals the total change over the extent.

    This is the property that makes the figure readable as "area = amount of change".
    """

    unified = 1000.0
    per_transition = 7.5  # hectares changing in every single transition

    for name, intervals in INTERVAL_GRIDS.items():
        bar_area = 0.0

        for start, end in intervals:
            duration = end - start
            interval_area = per_transition * duration
            height = (interval_area / duration) / unified * 100  # % per year
            bar_area += duration * height

        total = per_transition * N_TRANSITIONS / unified * 100

        assert abs(bar_area - total) < 1e-9, (name, bar_area, total)

        print('  4. area das barras %-4s OK  (%.4f %% == %.4f %%)' % (name, bar_area, total))


def test_unified_size():
    """The denominator is the union over the extent: every trajectory except 8."""

    assert legend.UNIFIED_SIZE_TRAJECTORIES == [1, 2, 3, 4, 5, 6, 7]
    assert legend.NEVER_PRESENT == 8
    assert 8 not in legend.UNIFIED_SIZE_TRAJECTORIES

    # a trajectory of 8 means absent in every year, by construction
    for length in range(2, 13):
        for presence in product([0, 1], repeat=length):
            if base_trajectory(presence) == 8:
                assert sum(presence) == 0, presence
            elif sum(presence) == 0:
                assert base_trajectory(presence) == 8, presence

    print('  5. unified size         OK  (trajetoria 8 == nunca presente, exaustivo)')


def test_legend_colors():
    """Every composite resolves to one of the 8 canonical colours."""

    canonical = {t['color'] for t in legend.TRAJECTORIES.values()}

    assert len(canonical) == 8, 'colours must be distinct: {}'.format(sorted(canonical))

    for row in legend.legend_rows():
        assert row['color'] in canonical, row
        assert row['color'] == legend.TRAJECTORIES[row['trajectory_id']]['color']

    # only 6 trajectories can appear in a figure, so the legend needs 6 entries, not 10
    appearing = {row['trajectory_id'] for row in legend.legend_rows()}
    assert appearing == set(legend.TRAJECTORIES_WITH_EVENTS) == {1, 2, 3, 4, 5, 6}

    print('  6. cores da legenda     OK  (10 compostos -> %d trajetorias distintas)'
          % len(appearing))


# ---------------------------------------------------------------------------
# The Code Editor twin, images/mapbiomas_brazil_annual_events_to_asset.js, repeats the
# years, the class list, the 49-class remap and the trajectory rules that live in
# statistics/config.py. Keeping it is a deliberate choice - it can show the result on a
# map - so the duplication is checked here rather than trusted.
# ---------------------------------------------------------------------------

JS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       '..', '..', 'images',
                       'mapbiomas_brazil_annual_events_to_asset.js')

PY_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       '..', '..', 'statistics', 'annual_events.py')


def _readJs():
    with io.open(JS_PATH, encoding='utf-8') as handle:
        source = handle.read()

    # drop // comments so their numbers cannot be mistaken for code
    return re.sub(r'//[^\n]*', '', source)


def _jsBlock(source, declaration):
    match = re.search(re.escape(declaration) + r'(.*?)\n(?:\}|\]);', source, re.S)

    assert match, 'block not found in the JS: {}'.format(declaration)

    return match.group(1)


def test_js_twin_years():
    source = _readJs()

    years = [int(value) for value in
             re.findall(r'\d{4}', _jsBlock(source, 'var years = ['))]

    assert years == YEARS, 'JS years differ from config.YEARS'

    print('  7. JS: anos            OK  (%d anos, 1985-2024)' % len(years))


def test_js_twin_classes():
    source = _readJs()

    pairs = re.findall(r"'class_name':\s*'([a-z_]+)',\s*'class_id':\s*(\d+)", source)

    js_classes = {name: int(value) for name, value in pairs}
    cfg_classes = {name: class_id for _, class_id, name in config.INTENSITY_CLASS_IDS}

    assert js_classes == cfg_classes, (
        'JS class list differs from config.INTENSITY_CLASS_IDS: {}'.format(
            set(js_classes.items()) ^ set(cfg_classes.items())))

    print('  8. JS: classes         OK  (%d, iguais a config)' % len(js_classes))


def test_js_twin_class_remap():
    source = _readJs()

    block = _jsBlock(source, 'var classRemap = {')

    js_remap = {int(key): int(value)
                for key, value in re.findall(r'(\d+):\s*(\d+)', block)}

    assert js_remap == config.CLASS_REMAP, (
        'JS classRemap differs from config.CLASS_REMAP on {}'.format(
            sorted(set(js_remap.items()) ^ set(config.CLASS_REMAP.items()))))

    print('  9. JS: classRemap      OK  (%d classes, iguais a config)' % len(js_remap))


def _whereValues(source, start, end):
    """The .where() values inside one function, identified by two markers.

    Scoped rather than global: both files also build the event bands with
    .where(loss, 1).where(gain, 2), which is a different code book.
    """

    begin = source.index(start)
    stop = source.index(end, begin)

    return [int(value) for value in
            re.findall(r'\.where\([^,]+,\s*(\d)\)', source[begin:stop])]


def test_js_twin_trajectory_rules():
    """The .where() chain must assign 1..8 in the same order on both sides.

    Order matters: later calls overwrite earlier ones, so a reordering silently changes
    the classification for pixels that match more than one condition.
    """

    js_source = _readJs()

    js_values = _whereValues(
        js_source, 'var baseTrajectory', "'trajectories_1985_2024'])")

    with io.open(PY_PATH, encoding='utf-8') as handle:
        py_source = handle.read()

    py_values = _whereValues(
        py_source, 'def baseTrajectory', 'config.BASE_TRAJECTORY_BAND])')

    expected = [1, 2, 3, 4, 5, 6, 7, 8]

    assert js_values == expected, 'JS trajectory rules out of order: {}'.format(js_values)
    assert py_values == expected, 'Python rules out of order: {}'.format(py_values)

    # the event code book, in both files: 1 = loss, 2 = gain
    js_events = _whereValues(js_source, 'var annualEvents', 'return ee.Image.cat')
    py_events = _whereValues(py_source, 'def annualEvents', 'return ee.Image.cat')

    assert js_events == [1, 2], js_events
    assert py_events == [1, 2], py_events

    print('  10. JS/Python: regras  OK  (ordem 1..8 e eventos 1=perda 2=ganho nos dois)')



if __name__ == '__main__':
    print('verificacoes time-intensity (sem GEE)\n')

    test_composite_rule()
    test_interval_grids()
    test_grid_equivalence()
    test_area_identity()
    test_unified_size()
    test_legend_colors()
    test_js_twin_years()
    test_js_twin_classes()
    test_js_twin_class_remap()
    test_js_twin_trajectory_rules()

    print('\ntudo OK')
