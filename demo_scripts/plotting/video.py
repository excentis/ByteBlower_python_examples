#!/usr/bin/python
""""
This example allows the user to configure a frameblasting flow which transmits data to the wireless endpoint.

WirelessEndpoint --> ByteBlowerPort
"""

from __future__ import print_function

from highcharts import Highchart

from .config import Style


def create_highcharts(device_name):
    chart = Highchart(width=1000, height=400)
    options = {
        'title': {
            'text': Style.title('Video Performance ' + device_name)
        },
        'chart': {
            'zoomType': 'x'
        },
        'xAxis': {
            'type': 'datetime',
            'title': {

                'text': Style.x_axis('Time [h:min:s]')
            }
        },
        'yAxis': [
            {
                'title': {
                    'text': Style.x_axis('Bytes')
                },
            }
        ],
    }
    chart.set_dict_options(options)

    return chart


def write_highcharts_html(chart, filename):
    with open(filename, 'w') as f:
        # Write the headers
        f.write(chart.htmlcontent)


def consolidate_datasets(results):
    """Reformats the dataset to 3 separate datasets so we can pass it easily to HighCharts"""

    out = []

    for item in ['buffer_size', 'bytes_downloaded', 'player_buffered_bytes_consumed']:
        resultset = []

        for result in results:
            # Highcharts just wants milliseconds since epoch
            ts_in_ms = int(result['timestamp'] / 1000000)
            resultset.append((ts_in_ms, result[item]))

        out.append(resultset)

    return out


def plot_data(device_name, results, filename):
    consolidated = consolidate_datasets(results)
    chart = create_highcharts(device_name)

    chart.add_data_set(consolidated[0], 'line', 'Buffer', yAxis=0)
    chart.add_data_set(consolidated[1], 'line', 'Downloaded', color='#EC008C', yAxis=0)
    chart.add_data_set(consolidated[2], 'line', 'Consumed', color='#00A650', yAxis=0)

    write_highcharts_html(chart, filename)
