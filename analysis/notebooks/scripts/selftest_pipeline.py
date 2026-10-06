"""End-to-end check of the time-intensity pipeline on synthetic data. No GEE needed.

Builds a fake exported GeoJSON with exactly the schema the export writes, pushes it
through the real loading, aggregation and plotting code, and asserts the properties the
figure depends on - above all that the area of the bars equals the total change.

Run with the project venv:  ../../.venv/bin/python selftest_pipeline.py
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                '..', '..', 'statistics'))

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402

import config  # noqa: E402
import trajectory_legend as legend  # noqa: E402
import tables  # noqa: E402
import time_intensity as ti  # noqa: E402
import plots  # noqa: E402

CATEGORY = 'country'
FEATURE_ID = '1'
CLASS_NAME = 'forest_formation'

UNIFIED_BY_TRAJECTORY = {1: 900.0, 2: 700.0, 3: 400.0, 4: 300.0,
                         5: 250.0, 6: 150.0, 7: 5000.0, 8: 99999.0}

# km2 changing in each single annual transition, per composite
PER_TRANSITION = {11: 3.0, 13: 2.0, 14: 1.0, 15: 1.5, 16: 0.5,
                  22: 2.5, 23: 1.2, 24: 2.2, 25: 1.5, 26: 0.5}


def feature(year1, year2, grid, data):
    return {
        'type': 'Feature',
        'geometry': None,
        'properties': {
            'featureid': FEATURE_ID,
            'year': year1 * 10000 + year2,
            'data': [[str(code), area] for code, area in data],
            'grid': grid,
            'collection': '10.0',
            'category': CATEGORY,
            'level_id': 2,
            'class_id': 3,
            'class_name': CLASS_NAME,
            'version': '1',
        },
    }


def syntheticGeoJson():
    features = [feature(config.FULL_EXTENT[0], config.FULL_EXTENT[1], 'base',
                        sorted(UNIFIED_BY_TRAJECTORY.items()))]

    for grid, intervals in config.INTERVAL_GRIDS.items():
        for year1, year2 in intervals:
            duration = year2 - year1
            data = [(code, area * duration) for code, area in sorted(PER_TRANSITION.items())]
            features.append(feature(year1, year2, grid, data))

    return {'type': 'FeatureCollection', 'features': features}


def main():
    folder = tempfile.mkdtemp(prefix='time-intensity-selftest-')
    path = os.path.join(folder, 'collection-10.0-time.intensity-country-'
                                '1985.2024-forest.formation-1.geojson')

    with open(path, 'w') as handle:
        json.dump(syntheticGeoJson(), handle)

    df = tables.loadFiles(path, valueName='composite_id', extraProperties=('grid',))
    df = ti.prepare(df)

    print('  carregado           OK  (%d linhas, colunas: %s)'
          % (len(df), ', '.join(sorted(df.columns))))

    # 1. denominator
    unified = ti.unifiedSize(df)
    expected = sum(UNIFIED_BY_TRAJECTORY[t] for t in legend.UNIFIED_SIZE_TRAJECTORIES) * 100
    got = float(unified['unified_size_ha'].iloc[0])
    assert abs(got - expected) < 1e-6, (got, expected)
    assert UNIFIED_BY_TRAJECTORY[8] * 100 not in (got,)
    print('  unified size        OK  (%.0f ha, trajetoria 8 excluida)' % got)

    # 2. per-composite totals of the grid
    totals = {}
    for grid in config.INTERVAL_GRIDS:
        table = ti.buildIntensityTable(df, grid)
        totals[grid] = table.groupby('composite_id')[ti.AREA_COLUMN].sum().to_dict()

    # 3. only the ten possible composites
    observed = set(int(c) for c in totals['5y'])
    assert observed == set(legend.COMPOSITES), sorted(observed)
    print('  compostos validos   OK  %s' % sorted(observed))

    # 4. averages agree with the per-interval numbers
    averages = ti.averageLines(df).iloc[0]
    for grid in config.INTERVAL_GRIDS:
        table = ti.buildIntensityTable(df, grid)
        for event, column in (('gain', 'gross_gain_pct_per_year'),
                              ('loss', 'gross_loss_pct_per_year')):
            rows = table[table['event'] == event]
            integrated = (rows['pct_of_unified_per_year'].astype(float)
                          * rows['duration_years']).sum() / config.N_TRANSITIONS
            assert abs(integrated - float(averages[column])) < 1e-9, (
                grid, event, integrated, averages[column])
    print('  linhas tracejadas   OK  (ganho %.4f %%/ano, perda %.4f %%/ano)'
          % (averages['gross_gain_pct_per_year'], averages['gross_loss_pct_per_year']))

    # 5. the figure identity: sum(width x height) == total change
    for grid in config.INTERVAL_GRIDS:
        table = ti.buildIntensityTable(df, grid)

        fig, ax = plt.subplots(figsize=(8, 4))
        plots.plotTimeIntensity(ax, table, averages,
                                title='selftest %s' % grid)

        gain_area = sum(p.get_width() * p.get_height()
                        for p in ax.patches if p.get_height() > 0)
        loss_area = sum(p.get_width() * -p.get_height()
                        for p in ax.patches if p.get_height() < 0)

        expected_gain = float(averages['gross_gain_pct_per_year']) * config.N_TRANSITIONS
        expected_loss = float(averages['gross_loss_pct_per_year']) * config.N_TRANSITIONS

        assert abs(gain_area - expected_gain) < 1e-6, (grid, gain_area, expected_gain)
        assert abs(loss_area - expected_loss) < 1e-6, (grid, loss_area, expected_loss)

        # bars must tile the axis with no gap and no overlap
        spans = sorted((p.get_x(), p.get_x() + p.get_width()) for p in ax.patches)
        merged = []
        for start, end in spans:
            if not merged or start > merged[-1][1] + 1e-9:
                merged.append([start, end])
            else:
                merged[-1][1] = max(merged[-1][1], end)
        assert len(merged) == 1, merged
        assert abs(merged[0][0] - 1985) < 1e-9 and abs(merged[0][1] - 2024) < 1e-9, merged

        # every colour must come from the canonical palette
        canonical = {t['color'].lower() for t in legend.TRAJECTORIES.values()}
        for patch in ax.patches:
            rgba = patch.get_facecolor()
            hexa = '#%02x%02x%02x' % tuple(int(round(c * 255)) for c in rgba[:3])
            assert hexa in canonical, hexa

        print('  figura %-4s         OK  (area ganho %.4f == %.4f, %d barras, x 1985-2024)'
              % (grid, gain_area, expected_gain, len(ax.patches)))

        plots.saveFigure(fig, os.path.join(folder, 'selftest-%s' % grid),
                         formats=('png',))

    # 6. rows must not collide after a spacing change, in either figure type
    folgas = {kind: rowClearance(kind) for kind in ('trajectories', 'components')}

    for kind, folga in folgas.items():
        assert folga > 4, '{}: linhas colidem, folga de {:.1f} px'.format(kind, folga)

    print('  6. folga entre linhas OK  (%s)' % ', '.join(
        '%s %.1f px' % (k, v) for k, v in folgas.items()))

    # 7. the one-axes components figure: column height == that class's total gross
    #    change, and the L/G mark agrees with the sign of the net change
    componentes = ti.componentsOfChange(df)
    classes = [CLASS_NAME] * 8

    fig, ax = plt.subplots(figsize=(6.45, 3.45))
    plots.plotComponentsByClass(ax, componentes, classes)

    alturas = {}
    for patch in ax.patches:
        alturas[round(patch.get_x() + patch.get_width() / 2.0, 6)] = (
            alturas.get(round(patch.get_x() + patch.get_width() / 2.0, 6), 0.0)
            + patch.get_height())

    linha = componentes.iloc[0]
    esperado = float(linha['quantity_pct_per_year']
                     + linha['exchange_pct_per_year']
                     + linha['alternation_pct_per_year'])

    assert len(ax.patches) == 3 * len(classes), len(ax.patches)
    assert len(alturas) == len(classes), sorted(alturas)

    for centro, altura in alturas.items():
        assert abs(altura - esperado) < 1e-9, (centro, altura, esperado)

    # the three components must reconstruct the total gross change
    total = float(linha['gross_gain_pct_per_year'] + linha['gross_loss_pct_per_year'])
    assert abs(esperado - total) < 1e-9, (esperado, total)

    # the mark is the side the net change falls on
    liquido = float(linha['endpoint_gain_ha'] - linha['endpoint_loss_ha'])
    marcas = {txt.get_text() for txt in ax.texts}
    esperada = plots.DIRECTION_MARK['gain' if liquido > 0 else 'loss']
    assert marcas == {esperada}, (marcas, esperada, liquido)

    # distinct columns must not overlap (the three segments of one column share a span)
    vaos = sorted({(round(patch.get_x(), 6),
                    round(patch.get_x() + patch.get_width(), 6))
                   for patch in ax.patches})
    assert len(vaos) == len(classes), vaos
    for (_, fim), (inicio, _) in zip(vaos, vaos[1:]):
        assert inicio >= fim - 1e-9, 'colunas se sobrepoem: %r > %r' % (fim, inicio)

    plots.saveFigure(fig, os.path.join(folder, 'selftest-components-by-class'),
                     formats=('png',))

    print('  7. componentes/classe OK  (%d colunas, altura %.4f == %.4f, marca %s)'
          % (len(alturas), list(alturas.values())[0], total, esperada))

    print('\ntudo OK - figuras de exemplo em %s' % folder)

    return folder




def rowClearance(kind='trajectories'):
    """Gap in pixels between one row's x tick labels and the next row's title.

    ROW_SPACING trades white space against panel height; below about 0.30 the two
    collide, and the collision is not obvious in a thumbnail. Called by main() with
    synthetic data so the guard runs without the exported tables.
    """
    import matplotlib.pyplot as plt

    import plots as p

    dados = syntheticGeoJson()

    folder = tempfile.mkdtemp(prefix='row-clearance-')
    path = os.path.join(folder, 'collection-10.0-time.intensity-country-'
                                '1985.2024-forest.formation-1.geojson')
    with open(path, 'w') as handle:
        json.dump(dados, handle)

    df = ti.prepare(tables.loadFiles(path, valueName='composite_id',
                                     extraProperties=('grid',)))

    tabela = ti.buildIntensityTable(df, '5y')
    componentes = ti.componentsOfChange(df)
    medias = ti.averageLines(df)

    # the synthetic file holds one class; repeat it so the grid has rows to compare
    classes = [CLASS_NAME] * 8

    fig = p.plotClassGrid(kind, tabela, componentes, medias, classes,
                          'Test', '5-year',
                          classLabels={CLASS_NAME: 'Test class'})

    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()

    eixos = sorted(fig.axes, key=lambda a: -a.get_position().y0)

    def baseDoEixo(ax):
        """Lowest ink under an axes: its tick labels, or its x label when it has none.

        The components panels set no ticks and carry an x label instead, so taking only
        tick labels raises on an empty sequence there.
        """

        alturas = [t.get_window_extent(renderer).y0
                   for t in ax.get_xticklabels() if t.get_visible()]

        rotulo = ax.xaxis.get_label()

        if rotulo.get_text():
            alturas.append(rotulo.get_window_extent(renderer).y0)

        return min(alturas) if alturas else ax.get_window_extent().y0

    menor = None
    for indice in range(0, len(eixos) - 2, 2):
        base = min(baseDoEixo(a) for a in eixos[indice:indice + 2])
        topo = max(a.title.get_window_extent(renderer).y1
                   for a in eixos[indice + 2:indice + 4])
        folga = base - topo
        menor = folga if menor is None else min(menor, folga)

    plt.close(fig)

    return menor


if __name__ == '__main__':
    print('verificacao ponta a ponta (sintetica, sem GEE)\n')
    main()
