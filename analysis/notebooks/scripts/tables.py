"""Shared helpers to turn the exported GeoJSON area files into formatted xlsx tables.

As in statistics/, collections 6 and 8 duplicated all of this in every table script.
Run these scripts from this directory: the data paths are relative to it.
"""
import json
import glob
from itertools import chain

import pandas as pd

# Properties written by the statistics scripts that describe the row, not the area
COMMON_PROPERTIES = ['category', 'version',
                     'level_id', 'class_id', 'class_name']


def loadFiles(file, valueName, extraProperties=()):
    """Reads one exported GeoJSON and returns a dataframe with one row per class/area.

    `valueName` is the name given to the first element of each `data` pair: the
    trajectory id, the number of changes, the number of classes or the stable class id.
    The `year` property holds `year1 * 10000 + year2`, written by
    statistics/trajectories_stats.py, and is decoded back into a `period` label here.
    """

    jsonData = json.loads(open(file).read())

    propList = map(lambda feature: feature['properties'], jsonData['features'])

    def buildRows(properties):

        base = {'feature_id': properties['featureid']}

        for key in list(COMMON_PROPERTIES) + list(extraProperties):
            if key in properties:
                base[key] = properties[key]

        base['period'] = '{}-{}'.format(
            int(properties['year'] / 10000), int(properties['year'] % 10000))

        return pd.DataFrame.from_records(
            map(lambda data: dict(base,
                                  **{valueName: int(data[0]),
                                     'area (hectare)': data[1] * 100}),
                properties['data']))

    return pd.concat(map(buildRows, propList))


def loadDataFrame(pathTemplate, categories, product, version, fileLabel, valueName,
                  extraProperties=()):
    """Globs every exported file for the given categories and concatenates them."""

    files = map(
        lambda category: glob.glob(
            pathTemplate.format(category, product, version, fileLabel)),
        categories
    )

    files = list(chain.from_iterable(files))

    if not files:
        raise SystemExit(
            'No files matched. Check data/JSON and the product/version values.')

    print('{} files'.format(len(files)))

    return pd.concat(
        map(lambda file: loadFiles(file, valueName, extraProperties), files))


def loadTerritory(territory_files):
    """Reads the territory shapefiles and drops the geometry column.

    geopandas is imported here, not at module level, so every other helper works
    without it. It is only needed to turn a feature_id into a territory name.
    """
    import geopandas as gpd

    territory = pd.concat(map(
        lambda file: gpd.read_file(file, encoding='utf8'),
        territory_files
    ))

    territory.pop('geometry')

    return territory


def pivotPeriods(df, indexColumns):
    """Pivots the period labels into columns of area in hectares."""

    dfp = pd.pivot_table(df,
                         index=indexColumns,
                         columns='period',
                         values='area (hectare)',
                         fill_value=0)

    return dfp.reset_index()


def splitTerritoryNames(dfp, categories):
    """Cleans `name_pt_br` and splits the compound names used by some categories."""

    if 'name_pt_br' not in dfp.columns:
        return dfp

    dfp['name_pt_br'] = dfp['name_pt_br'].replace(r'\(+', '- ', regex=True)
    dfp['name_pt_br'] = dfp['name_pt_br'].replace(r'\)+', '', regex=True)

    if 'CITY' in categories:
        parts = ['city', 'state']
    elif 'BIOMES_PER_STATE' in categories:
        parts = ['biome', 'state']
    else:
        return dfp

    dfp[parts] = dfp['name_pt_br'].str.split(' - ', expand=True)

    first, second = dfp.pop(parts[0]), dfp.pop(parts[1])

    dfp.pop('name_pt_br')

    if 'name_en' in dfp.columns:
        dfp.pop('name_en')

    dfp.insert(0, parts[0], first)
    dfp.insert(0, parts[1], second)

    return dfp


def writeExcel(dfp, xlsx_file):
    """Writes the table with the MapBiomas header/body formatting."""

    writer = pd.ExcelWriter(xlsx_file, engine='xlsxwriter')

    dfp.to_excel(writer, index=False, sheet_name="Sheet1")

    workbook = writer.book

    worksheet = writer.sheets['Sheet1']

    cell_format = workbook.add_format({
        'font_name': 'Fira Sans Book',
        'size': 10
    })

    worksheet.set_column('A1:CZ500000', None, cell_format)

    header_format = workbook.add_format({
        'font_name': 'Fira Sans Book',
        'bold': True,
        'size': 10,
        'fg_color': '#151515',
        'color': '#ffffff',
    })

    for col, value in enumerate(dfp.columns.values):
        worksheet.write(0, col, value, header_format)

    writer.close()

    print(xlsx_file)


def _formatSheet(writer, dfp, sheetName):
    """Applies the MapBiomas header/body formatting to one sheet."""

    workbook = writer.book

    worksheet = writer.sheets[sheetName]

    cell_format = workbook.add_format({
        'font_name': 'Fira Sans Book',
        'size': 10
    })

    worksheet.set_column('A1:CZ500000', None, cell_format)

    header_format = workbook.add_format({
        'font_name': 'Fira Sans Book',
        'bold': True,
        'size': 10,
        'fg_color': '#151515',
        'color': '#ffffff',
    })

    for col, value in enumerate(dfp.columns.values):
        worksheet.write(0, col, value, header_format)


def writeExcelSheets(sheets, xlsx_file):
    """Writes several dataframes as separate sheets of one formatted workbook.

    `sheets` maps sheet name to dataframe, in the order they should appear.
    """

    writer = pd.ExcelWriter(xlsx_file, engine='xlsxwriter')

    for sheetName, dfp in sheets.items():
        dfp.to_excel(writer, index=False, sheet_name=sheetName)
        _formatSheet(writer, dfp, sheetName)

    writer.close()

    print(xlsx_file)

    return xlsx_file
