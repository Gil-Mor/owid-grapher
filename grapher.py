import sys
import os
from typing import List, Dict
import pandas as pd
import argparse
import glob
import re
from bokeh.models import ColumnDataSource
from bokeh.plotting import figure, output_file, save
from bokeh.palettes import Category10_10 as palette
import itertools


def parse_columns(raw_columns: List[str], col_index_name_map: Dict[int, str]):
    return [get_val_from_index_str_map(col_index_name_map, c) for c in raw_columns]


def escape_filename_str(s: str):
    ''' Escapes str for filename '''
    res = re.sub(r'\W+', '_', s)
    return res


def prepare_subplots_plot(p, col_name: str, country_str: str, country_color_map: Dict[str, str], country_color: str):
    # If subplots so each plot is for different column
    # so put columns as y axis label,
    # else, y axis is for multiple columns so keep label empty
    # and put all info in legend.
    p.yaxis.axis_label = col_name
    legend = country_str
    if country_str not in country_color_map:
        # If subplots keep colors the same for same country accross plots
        country_color_map[country_str] = country_color
    color = country_color_map[country_str]
    return p, legend, color


def prepare_single_plot(p, col_name: str, country_str: str, country_color_map: Dict[str, str], country_color: str):
    legend = country_str + " " + col_name
    # If single plot change colors for countries for different columns
    color = country_color
    return p, legend, color


def prepare_output_file(title: str, output: str):
    if not output:
        output = 'out/' + escape_filename_str(title) + ".html"
    else:
        output += ".html"
    try:
        os.makedirs(os.path.dirname(output), exist_ok=True)
    except:
        pass
    return output


def plot_with_bokeh(df: pd.DataFrame, title: str, subplots: bool, output: str):
    colors = itertools.cycle(palette)

    output = prepare_output_file(title, output)

    output_file(output)

    cols = df.columns[2:]
    figs = [figure(plot_width=1000, x_axis_label='Day')]
    country_color_map = {}
    for col in cols:
        if subplots and col != cols[0]:
            figs += [figure(plot_width=1000, x_axis_label='Day')]
        p = figs[-1]
        for (country_str, country_df), country_color in zip(df.groupby('Country'), colors):
            source = ColumnDataSource(data=country_df)
            if subplots:
                p, legend, color = prepare_subplots_plot(
                    p, col, country_str, country_color_map, country_color)
            else:
                p, legend, color = prepare_single_plot(
                    p, col, country_str, country_color_map, country_color)
            p.line(x='Day', y=col, legend_label=legend,
                   color=color, source=source)
            p.legend.location = 'top_left'  # if inside plot area set in top left
            p.legend.click_policy = "hide"

    # Move legend out of plot in case of single plot because legend needs to contain
    # all info and will take too much space.
    if not subplots:
        p.plot_width = 1400  # make plot larger because legend takes space
        p.add_layout(p.legend[0], 'right')

    print("output file: " + output)
    save(figs)


def list_datasets(filters: List[str]):
    l = [d.replace('owid-datasets/datasets/', '')
         for d in glob.glob('owid-datasets/datasets/*')]
    if filters:
        l = list(filter(lambda filename: any(
            [f.lower() in filename.lower() for f in filters]), l))
    res = dict([(i, d) for i, d in enumerate(l)])
    return res


def get_val_from_index_str_map(d: Dict[int, str], key: str):
    res = key
    if key.isdigit():
        res = d[int(key)]
    return res


def get_dataset_filename(ds_arg: str, ds_list: Dict[int, str]):
    return get_val_from_index_str_map(ds_list, ds_arg)


def get_dataset(datasets: List, dataset_index_map: Dict[int, str]):
    frames = []
    for ds in datasets:
        frames += [pd.read_csv(
            'owid-datasets/datasets/{0}/{0}.csv'.format(get_dataset_filename(ds, dataset_index_map)))]

    return pd.concat(frames)


def main(args: List[str]):

    ds_list = list_datasets(args.filter_datasets)
    if args.list_datasets:
        for i, d in ds_list.items():
            print('{}. {}'.format(i, d))
        return

    if not args.datasets:
        raise "missing datasets input."

    csv_data = get_dataset(args.datasets, ds_list)

    if args.head:
        print(csv_data.head())
        return

    # Change from Entity, Year
    csv_data.columns.values[0], csv_data.columns.values[1] = "Country", "Day"

    # print columns names
    if args.col_names:
        for i, c in enumerate(csv_data.columns.values.tolist()):
            print("{}. {}".format(i, c))
        return

    col_index_name_map = dict(
        [(k, v) for k, v in enumerate(csv_data.columns.values.tolist())])

    columns = ['Country', 'Day'] + \
        parse_columns(args.columns, col_index_name_map)

    csv_data = csv_data.filter(items=columns)
    title = "{}\n{}\nper {}".format(
        ', '.join(args.countries), '\n'.join(columns[2:]), ', '.join(columns[:2]))

    print('title: ' + title)

    data = pd.concat([csv_data.query('Country == "{}"'.format(c))
                      for c in args.countries])

    plot_with_bokeh(data, title, args.subplots, args.output)


def parse_args(argv: List[str] = sys.argv):
    parser = argparse.ArgumentParser(
        description='Process and plot graphs from OWID Covid datasets.\nhttps://github.com/owid/owid-datasets')
    parser.add_argument('-d', '--datasets', type=str, nargs='+', default=['COVID-2019 - ECDC (2020)'],
                        help='Choose datasets to work with. You can use name or index. For index use the --list-datasets option and optionally the --filter-datasets option')
    parser.add_argument('-l', '--list-datasets', action='store_true',
                        help='Print list of datasets. Use with --filter-datasets to filter list by keywords.')
    parser.add_argument('-f', '--filter-datasets', nargs='*', default=['covid'],
                        help='Filter datasets list with patterns (e.g. covid deaths poverty \'Extreme Temperatures\' etc..). The patterns are case insensitive. For multi word pattern enclose in quotes (\'Extreme Temperatures\').\n'
                        'If you used this option when printing the list of datasets, use the same pattern when choosing a dataset so that index will be the same.\n'
                        'Default is \'covid\'. You can disable by specifying an empty filters (-f) or another filter(-f poverty), but the script was not tested with other datasets.')
    parser.add_argument('-c', '--columns', nargs='+', type=str, default=['2'],
                        help='Choose columns. Can choose by name or index. '
                        'For index use the -cn/--col-names option to print columns names. '
                        'Columns 0 and 1 are usually Country and Date and are used automatically to parse data')
    parser.add_argument('-cn', '--col-names', action='store_true',
                        help='Print indexed list of the csv columns names.'
                        'You can use the names or indexes for queries.')
    parser.add_argument('-head', action='store_true',
                        help='Print first rows of a dataset for example values.')
    parser.add_argument('-co', '--countries', help='Countries.',
                        type=str, nargs='+', default=['Germany'])
    parser.add_argument('-o', '--output', type=str, default='',
                        help='Output file. If empty a name will be prepared from other arguments.\nNOTE: Give only a filename. file type will be determined by the scripts (png, html, etc..).')
    parser.add_argument('-sp', '--subplots', action='store_true',
                        help='Will plot every columns in a new graph.\n'
                        'This is an easy way to handle different y values scales (e.g. [0-1] vs [0-100000]).')
    parser.add_argument('--no-sp', '--no-subplots', dest='subplots', action='store_false',
                        help='Will plot all columns in a single graph.')
    parser.set_defaults(subplots=True)

    args = parser.parse_args()
    return args


if __name__ == "__main__":
    main(parse_args())
