#!/usr/bin/python
""""
This example allows the user to configure a frameblasting flow which transmits data to the wireless endpoint.

WirelessEndpoint --> ByteBlowerPort
"""

from __future__ import print_function

from time import mktime
from highcharts import Highchart
import csv
import datetime

def create_highcharts(device_name, results):

    categories = []
    ssid_categories = results[3]
    for pair in ssid_categories:
        categories.append(pair[1])

    chart = Highchart(width=1000, height=400)
    styling = '<span style="font-family: \'DejaVu Sans\', Arial, Helvetica, sans-serif; color: '
    options = {
        'title': {
            'text': styling + '#00AEEF; font-size: 20px; line-height: 1.2640625; ">' + 'Wi-Fi Performance ' + device_name + '</span>'
        },
        'chart': {
            'zoomType': 'x'
        },
        'xAxis': {
            'type': 'datetime',
            'title': {
                'text': styling + '#F7941C; font-size: 12px; line-height: 1.4640625; font-weight: bold;">Time [h:min:s]</span>'
            }
        },
        'yAxis': [
            {
                'title': {
                    'text': styling + '#00AEEF; font-size: 12px; line-height: 1.2640625; font-weight: bold; ">Throughput [bps]</span>'
                },
                'min':0,
            }, {
                'title': {
                    'text': styling + '#EC008C; font-size: 12px; line-height: 1.2640625; font-weight: bold; ">RSSI</span>'
                },
                # 'angle': '45',
                # 'min': -127,
                'opposite': 'true'
            }, {
                'title': {
                    'text': styling + '#00A650; font-size: 12px; line-height: 1.2640625; font-weight: bold; ">SSID/BSSID</span>'
                },
                # 'labels': {
                #     'rotation': 45,
                # },
                # 'min': 0,
                'min': 0,
                'categories': categories,
                'opposite': 'true'
            }
        ],
    }
    chart.set_dict_options(options)

    return chart

def write_highcharts_html(chart):
    with open('highcharts_rssi.html', 'w') as f:
        # Write the headers
        f.write(chart.htmlcontent)

def plot_data(device_name, results_filename):
    print("Reading CSV results from file ", results_filename)
    # desired_keys = ['timestamp', 'tx_frames', 'rx_frames', 'loss', 'throughput', 'rssi']
    results = read_from_csv(results_filename)
    chart = create_highcharts(device_name, results)

    chart.add_data_set(results[0], 'line', 'Throughput', yAxis=0)
    chart.add_data_set(results[1], 'line', 'RSSI', color='#EC008C', yAxis=1)
    chart.add_data_set(results[2], 'line', 'SSID/BSSID', color='#00A650', yAxis=2)

    yAxis = chart.options.get('yAxis')
    write_highcharts_html(chart)


def get_millis(timestring):
    datetime_object = datetime.datetime.strptime(timestring, '%Y-%m-%d %H:%M:%S')
    sec_since_epoch = mktime(datetime_object.timetuple()) + datetime_object.microsecond / 1000000.0
    millis = sec_since_epoch * 1000
    return millis

no_signal = 'No Signal'

# return the index of the ssid_bssid:
def append_ssid_bssid(categories, ssid_bssid):
    i = 0
    if ssid_bssid == ' <br> 00:00:00:00:00:00':
        ssid_bssid = no_signal
    while i < len(categories):
        pair = categories[i]
        if pair[1] == ssid_bssid:
            return i
        i+=1
    categories.append([i,ssid_bssid])
    return i

def read_from_csv(results_file):
    throughput_series = []
    rssi_series = []
    ssid_bssid_series = []
    ssid_bssid_categories = [[0,no_signal]]

    skipheader = True
    with open(results_file) as csvfile:
        readCSV = csv.reader(csvfile, delimiter=',')
        for row in readCSV:
            if skipheader:
                skipheader = False
            else:
                millis = get_millis(row[0])
                throughput_series.append([millis,float(row[4])])
                rssi_series.append([millis,float(row[5])])
                ssid_bssid = row[6] + ' <br> ' + row[7]
                index = append_ssid_bssid(ssid_bssid_categories, ssid_bssid)
                ssid_bssid_series.append([millis, index])

    # print(throughput_series)
    # print(rssi_series)
    print(ssid_bssid_series)

    all_series = []
    all_series.append(throughput_series)
    all_series.append(rssi_series)
    all_series.append(ssid_bssid_series)
    all_series.append(ssid_bssid_categories)
    return all_series

if __name__ == '__main__':
    device_name = 'Samsung S10'
    results_file = 'rssi_vs_udp_loss.py.csv'
    plot_data(device_name, results_file)
