"""Builds the time-intensity xlsx tables from the exported GeoJSON.

Run from this directory, with the project venv:
    ../../.venv/bin/python mapbiomas_brazil_time_intensity_tables.py

One workbook per interval grid, with five sheets: the tidy table the figures are drawn
from, a wide human-readable pivot, the unified-size denominator, the dashed-line
averages, and the reconstructed composite legend.
"""
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                '..', '..', 'statistics'))

import config  # noqa: E402
import tables  # noqa: E402
import time_intensity as ti  # noqa: E402

# Territory folders written by the export. Uncomment to add more.
OBJ = [
    {
        'category': ['COUNTRY'],
        'product': 'INTENSIDADE-TEMPO',
        'version': config.OUTPUT_VERSION,
        # optional: needs geopandas, only to turn feature_id into a territory name
        'territory_files': [],
        'output_name': 'brazil-time-intensity-c10',
        'output_version': '1a',
    },
]

# {category}/{product}-{version}/*{file label}*
PATH = '../../data/JSON/{}/{}-{}/*{}*'

FILE_LABEL = 'time.intensity'

OUTPUT_FOLDER = '../../data/TABLES'


def load(obj):
    """Loads every exported file for this entry into one dataframe."""

    df = tables.loadDataFrame(
        pathTemplate=PATH,
        categories=obj['category'],
        product=obj['product'],
        version=obj['version'],
        fileLabel=FILE_LABEL,
        valueName='composite_id',
        extraProperties=('grid',))

    return ti.prepare(df)


def addTerritoryNames(df, territory_files):
    """Joins the territory names when the shapefiles are available.

    Optional on purpose: the figures work with feature_id alone, and geopandas is not
    needed for anything else in this pipeline.
    """

    if not territory_files:
        df = df.copy()
        df['territory'] = [config.territoryName(c, f)
                           for c, f in zip(df['category'], df['feature_id'])]
        return df

    territory = tables.loadTerritory(territory_files)

    df = territory.merge(df, on='feature_id', how='inner')

    name_column = 'name_pt_br' if 'name_pt_br' in df.columns else 'feature_id'
    df['territory'] = df[name_column]

    return df


for obj in OBJ:

    df = load(obj)

    print(df.head())

    for grid in config.INTERVAL_GRIDS:

        table = ti.buildIntensityTable(df, grid)
        table = addTerritoryNames(table, obj['territory_files'])

        averages = addTerritoryNames(ti.averageLines(df), obj['territory_files'])

        components = ti.componentsOfChange(df)
        ti.checkComponents(components)
        components = addTerritoryNames(components, obj['territory_files'])

        unified = addTerritoryNames(
            ti.splitComposite(df[df['grid'] == 'base'].rename(
                columns={'composite_id': 'composite_id'})).assign(
                    trajectory_id=lambda frame: frame['composite_id']),
            obj['territory_files'])

        wide = table.pivot_table(
            index=['territory', 'category', 'feature_id', 'class_name', 'event',
                   'trajectory_id', 'trajectory_label_en'],
            columns='period',
            values='pct_of_unified_per_year',
            fill_value=0).reset_index()

        sheets = {
            'intensity': table,
            'intensity_wide': wide,
            'unified_size': unified[
                ['territory', 'category', 'feature_id', 'class_name',
                 'trajectory_id', ti.AREA_COLUMN]],
            'averages': averages,
            'components': components,
            'legend': ti.legendTable(),
        }

        xlsx_file = os.path.join(OUTPUT_FOLDER, '{}-{}-{}.xlsx'.format(
            obj['output_name'], grid, obj['output_version']))

        tables.writeExcelSheets(sheets, xlsx_file)
