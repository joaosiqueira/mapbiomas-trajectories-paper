"""Canonical trajectory legend, and the composite legend used by the time-intensity figures.

Two code books live here.

`TRAJECTORIES` is the base one: the 8 categories of Bilintoh, Pontius & Zhang (2024),
computed over the full 1985-2024 extent. Ids, labels and colors are the ones already
hardcoded in trajectories.js; this module is only a single place to read them from.

`COMPOSITES` is the crossing used by the time-intensity statistics, using the
encoding `annual_event * 10 + base_trajectory`:

    tens  1 = the class was lost between year y and y+1
          2 = the class was gained between year y and y+1
    units 1..8 = the pixel's trajectory over the whole 1985-2024 extent

Only 10 of the 16 conceivable composites can ever occur, and this is provable rather
than conventional: a pixel whose base trajectory is 7 (Presence->Stable->Presence) or
8 (Absence->Stable->Absence) has zero changes over the extent, so it can carry no
annual event at all; and a base trajectory of 1 or 2 has exactly one change, which must
have the same direction as the trajectory itself. notebooks/scripts/selftest_time_intensity.py
proves the set by exhaustive enumeration.

`write_xlsx()` writes the same code book as a spreadsheet.
"""

LOSS = 1
GAIN = 2

EVENTS = {
    LOSS: {'name_en': 'Loss', 'name_pt_br': 'Perda'},
    GAIN: {'name_en': 'Gain', 'name_pt_br': 'Ganho'},
}

# id: the paper's Table 2 name, the path it describes, and the colour.
# `name_en` is the name used in figures and tables; `path_en` spells out the sequence,
# which is what the name means but is too long for a legend entry.
TRAJECTORIES = {
    1: {'color': '#941004',
        'name_en': 'Loss without Alternation',
        'name_pt_br': 'Perda sem Alternancia',
        'path_en': 'Presence->Loss->Absence'},
    2: {'color': '#020e7a',
        'name_en': 'Gain without Alternation',
        'name_pt_br': 'Ganho sem Alternancia',
        'path_en': 'Absence->Gain->Presence'},
    3: {'color': '#f5261b',
        'name_en': 'Loss with Alternation',
        'name_pt_br': 'Perda com Alternancia',
        'path_en': 'Presence->Alternation->Loss->Absence'},
    4: {'color': '#14a5e3',
        'name_en': 'Gain with Alternation',
        'name_pt_br': 'Ganho com Alternancia',
        'path_en': 'Absence->Alternation->Gain->Presence'},
    5: {'color': '#8b8000',
        'name_en': 'All Alternation Loss First',
        'name_pt_br': 'Toda Alternancia, Perda Primeiro',
        'path_en': 'Presence->Alternation->Presence'},
    6: {'color': '#ffff00',
        'name_en': 'All Alternation Gain First',
        'name_pt_br': 'Toda Alternancia, Ganho Primeiro',
        'path_en': 'Absence->Alternation->Absence'},
    7: {'color': '#666666',
        'name_en': 'Stable Presence',
        'name_pt_br': 'Presenca Estavel',
        'path_en': 'Presence->Stable->Presence'},
    8: {'color': '#cfcfcf',
        'name_en': 'Stable Absence',
        'name_pt_br': 'Ausencia Estavel',
        'path_en': 'Absence->Stable->Absence'},
}

# Base trajectories that can carry an annual change event. 7 and 8 have zero changes.
TRAJECTORIES_WITH_EVENTS = [1, 2, 3, 4, 5, 6]

# The only composites that can occur. Proven in selftest_time_intensity.py.
LOSS_COMPOSITES = [11, 13, 14, 15, 16]
GAIN_COMPOSITES = [22, 23, 24, 25, 26]
COMPOSITES = LOSS_COMPOSITES + GAIN_COMPOSITES

# Base trajectory ids that are never present at all -> excluded from the unified size
NEVER_PRESENT = 8

# Base trajectory ids whose union is the class's "unified size" over the extent
UNIFIED_SIZE_TRAJECTORIES = [1, 2, 3, 4, 5, 6, 7]


def split_composite(composite_id):
    """Returns (event_id, trajectory_id) for a composite such as 13 or 26."""

    return composite_id // 10, composite_id % 10


def is_valid_composite(composite_id):
    """True when the composite is one of the 10 that can physically occur."""

    return composite_id in COMPOSITES


def describe(composite_id):
    """Full description of one composite, as used in the xlsx and the figure legend."""

    event_id, trajectory_id = split_composite(composite_id)

    if not is_valid_composite(composite_id):
        raise ValueError(
            'composite {} cannot occur: event {} on base trajectory {}'.format(
                composite_id, event_id, trajectory_id))

    event = EVENTS[event_id]
    trajectory = TRAJECTORIES[trajectory_id]

    return {
        'composite_id': composite_id,
        'event_id': event_id,
        'event_en': event['name_en'],
        'event_pt_br': event['name_pt_br'],
        'trajectory_id': trajectory_id,
        'trajectory_en': trajectory['name_en'],
        'trajectory_pt_br': trajectory['name_pt_br'],
        'trajectory_path': trajectory['path_en'],
        # the segment takes the colour of the BASE trajectory; the side of the axis
        # (above/below zero) is what carries the event, exactly as in the legacy chart
        'color': trajectory['color'],
        'name_en': '{}: {}'.format(event['name_en'], trajectory['name_en']),
        'name_pt_br': '{}: {}'.format(event['name_pt_br'], trajectory['name_pt_br']),
    }


def legend_rows():
    """The 10 composites, loss first, as plain dicts."""

    return [describe(composite_id) for composite_id in COMPOSITES]


def trajectory_rows():
    """The 8 base trajectories as plain dicts."""

    return [dict(trajectory_id=key, **value) for key, value in sorted(TRAJECTORIES.items())]


def write_xlsx(path):
    """Writes the code book as data/TABLES/legenda-trajetorias.xlsx.

    Sheet `trajetorias` holds the 8 base categories, keyed by `trajectory_id`, which is
    the key the existing table scripts join on. Sheet `compostos` holds the 10 crossed
    categories used by the time-intensity tables.
    """
    import pandas as pd

    trajectories = pd.DataFrame(trajectory_rows())[
        ['trajectory_id', 'name_en', 'name_pt_br', 'path_en', 'color']]

    composites = pd.DataFrame(legend_rows())[
        ['composite_id', 'event_id', 'event_en', 'event_pt_br',
         'trajectory_id', 'trajectory_en', 'trajectory_pt_br', 'trajectory_path',
         'name_en', 'name_pt_br', 'color']]

    with pd.ExcelWriter(path, engine='xlsxwriter') as writer:
        trajectories.to_excel(writer, index=False, sheet_name='trajetorias')
        composites.to_excel(writer, index=False, sheet_name='compostos')

    print(path)

    return path


if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1:
        write_xlsx(sys.argv[1])
    else:
        for row in legend_rows():
            print('%3d  %-6s  %-38s  %s' % (
                row['composite_id'], row['event_en'], row['trajectory_en'], row['color']))
