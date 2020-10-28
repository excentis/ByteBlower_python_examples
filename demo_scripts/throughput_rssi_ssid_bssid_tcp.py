""""


"""

from __future__ import print_function
import time
import random
import datetime

from byteblowerll.byteblower import ByteBlower, DeviceStatus, ConfigError
from byteblowerll.byteblower import NetworkInterfaceType

from highcharts import Highchart
import os
import sys
import csv
import datetime
from time import mktime

configuration = {
    # Address (IP or FQDN) of the ByteBlower server to use
    'server_address': '10.10.1.204',

    # Interface on the server to create a port on.
    'server_interface': 'nontrunk-1',

    # MAC address of the ByteBlower port which will be generated
    'port_mac_address': '00:bb:01:00:00:01',

    # DHCP or IP configuration for the ByteBlower port
    # if DHCP, use "dhcp"
    'port_ip_address': 'dhcp',
    # if static, use ["ipaddress", "netmask", "gateway"]
    # 'port_ip_address': ['172.16.0.4', '255.255.252.0', '172.16.0.1'],

    # Address (IP or FQDN) of the ByteBlower Meetingpoint to use.  The wireless
    # endpoint *must* be registered on this meetingpoint.
    # Special value: None.  When the address is set to None, the server_address
    #                       will be used.
    'meetingpoint_address': None,

    # UUID of the ByteBlower WirelessEndpoint to use.  This wireless endpoint
    # *must* be registered to the meetingpoint  configured by
    # meetingpoint_address.
    # Special value: None.  When the UUID is set to None, the example will
    #                       automatically select the first available wireless
    #                       endpoint.
    #'wireless_endpoint_uuid': None,
    'wireless_endpoint_uuid': 'eda84fd1f0761a6d',

    # Name of the WiFi interface to query.
    # Special value: None.  None will search for an interface with type WiFi.
    # 'wireless_interface': None,
    'wireless_interface': 'wlan0',

    # TCP port for the HTTP server
    'port_tcp_port': 4096,

    # TCP port for the HTTP Client
    'wireless_endpoint_tcp_port': 4096,

    # HTTP Method
    # HTTP Method can be GET or PUT
    # - GET: Standard HTTP download, we retrieve data from the web server
    # - PUT: Standard HTTP upload, the wireless endpoint will push data to the
    #        webserver
    # 'http_method': 'GET',
    'http_method': 'PUT',
    
    # duration, in nanoseconds
    # Duration of the session
    #           sec  milli  micro  nano
    'duration': 10 * 1000 * 1000 * 1000,

    # TOS value to use on the HTTP client (and server)
    'tos': 0
}


class Example:
    def __init__(self, **kwargs):
        self.server_address = kwargs['server_address']
        self.server_interface = kwargs['server_interface']
        self.port_mac_address = kwargs['port_mac_address']
        self.port_ip_address = kwargs['port_ip_address']

        self.meetingpoint_address = kwargs['meetingpoint_address']
        if self.meetingpoint_address is None:
            self.meetingpoint_address = self.server_address

        self.wireless_endpoint_uuid = kwargs['wireless_endpoint_uuid']
        self.wireless_interface = kwargs['wireless_interface']

        self.port_tcp_port = kwargs['port_tcp_port']
        self.wireless_endpoint_tcp_port = kwargs['wireless_endpoint_tcp_port']

        # Helper function, we can use this to parse the HTTP Method to the
        # enumeration used by the API
        from byteblowerll.byteblower import ParseHTTPRequestMethodFromString

        self.http_method = ParseHTTPRequestMethodFromString(kwargs['http_method'])
        self.duration = kwargs['duration']
        self.tos = kwargs['tos']

        self.server = None
        self.port = None
        self.meetingpoint = None
        self.wireless_endpoint = None
        self.network_info_monitor = None

    def run(self):

        # duration of the samples taken. (nanoseconds)
        sample_duration = 1000000000

        # number of samples to take:
        # ( test_duration / sample_duration) is just enough, so we are doubling
        # this so we have more than enough
        sample_count = int(2 * (self.duration / sample_duration))

        instance = ByteBlower.InstanceGet()

        # Connect to the server
        self.server = instance.ServerAdd(self.server_address)

        # create and configure the port.
        self.port = self.server.PortCreate(self.server_interface)

        # configure the MAC address on the port
        port_layer2_config = self.port.Layer2EthIISet()
        port_layer2_config.MacSet(self.port_mac_address)

        # configure the IP addressing on the port
        port_layer3_config = self.port.Layer3IPv4Set()
        if type(self.port_ip_address) is str and self.port_ip_address == 'dhcp':
            # DHCP is configured on the DHCP protocol
            dhcp_protocol = port_layer3_config.ProtocolDhcpGet()
            dhcp_protocol.Perform()
        else:
            # Static addressing
            port_layer3_config.IpSet(self.port_ip_address[0])
            port_layer3_config.NetmaskSet(self.port_ip_address[1])
            port_layer3_config.GatewaySet(self.port_ip_address[2])

        print("Created port", self.port.DescriptionGet())

        # Connect to the meetingpoint
        self.meetingpoint = instance.MeetingPointAdd(self.meetingpoint_address)

        # If no WirelessEndpoint UUID was given, search an available one.
        if self.wireless_endpoint_uuid is None:
            self.wireless_endpoint_uuid = self.select_wireless_endpoint_uuid()

        # Get the WirelessEndpoint device
        self.wireless_endpoint = self.meetingpoint.DeviceGet(self.wireless_endpoint_uuid)
        print("Using wireless endpoint", self.wireless_endpoint.DescriptionGet())

        # Now we have the correct information to start configuring the flow.

        # Claim the wireless endpoint for ourselves.  This means that nobody
        # but us can use this device.
        self.wireless_endpoint.Lock(True)

        # Configure the HTTP server, running on the ByteBlower port.
        http_server = self.port.ProtocolHttpServerAdd()
        if self.port_tcp_port is None:
            self.port_tcp_port = random.randint(10000, 40000)

        # Configure the TCP port on which the HTTP server wll listen
        http_server.PortSet(self.port_tcp_port)

        # Configure the receive window.
        http_server.ReceiveWindowScalingEnable(True)
        http_server.ReceiveWindowScalingValueSet(7)

        # Tell the ByteBlower to sample every sample_duration and keep up to
        # sample_count samples (see top of this function)
        http_server.HistorySamplingIntervalDurationSet(sample_duration)
        http_server.HistorySamplingBufferLengthSet(sample_count)

        # A HTTP server will not listen for new connections as long it is not
        # started.  You can compare it to e.g. Apache or nginx, it won't accept
        # new connections as long the daemon is not started.
        http_server.Start()

        print("HTTP server configuration:", http_server.DescriptionGet())

        # Configure the client.
        http_client = self.wireless_endpoint.ProtocolHttpClientAdd()
        # Configure the remote endpoint to which it must connect.
        # This is the IP address and port of the HTTP server configured above
        http_client.RemoteAddressSet(self.port.Layer3IPv4Get().IpGet())
        http_client.RemotePortSet(self.port_tcp_port)

        http_client.RequestDurationSet(self.duration)
        http_client.RequestInitialTimeToWaitSet(0)
        # What will we do? HTTP Get or HTTP PUT?
        http_client.HttpMethodSet(self.http_method)

        http_client.TypeOfServiceSet(self.tos)

        print("HTTP client configuration:", http_client.DescriptionGet())

        # Add a NetworkInfoMonitor, to monitor the RSSI over time :
        device_info = self.wireless_endpoint.DeviceInfoGet()
        self.network_info_monitor = device_info.NetworkInfoMonitorAdd()

        # Send the scenario to the wireless endpoint
        self.wireless_endpoint.Prepare()

        # Start the wireless endpoint.
        # Actually, the function will return earlier, since the MeetingPoint
        # schedules the start some time in the future, to make sure all
        # devices start at the same time.
        self.wireless_endpoint.Start()

        # Wait until the device returns.
        # As long the device is running, the device will be in
        # - DeviceStatus_Starting
        # - DeviceStatus_Running
        # As soon the device has finished the test, it will return to
        # 'DeviceStatus_Reserved', since we have a Lock on the device.
        status = self.wireless_endpoint.StatusGet()
        start_moment = datetime.datetime.now()
        while status != DeviceStatus.Reserved:
            time.sleep(1)
            status = self.wireless_endpoint.StatusGet()
            now = datetime.datetime.now()
            print(str(now), ":: Running for", str(now - start_moment), "::",
                  http_server.ClientIdentifiersGet().size(), "client(s) connected")

        # Wireless Endpoint has returned. Collect and process the results.

        # Fetch the results from the wireless endpoint, they will be stored
        # at the MeetingPoint, we will fetch the results in a following step.
        self.wireless_endpoint.ResultGet()

        # Fetch the results of our created NetworkInfoMonitor
        network_info_history = self.network_info_monitor.ResultHistoryGet()
        network_info_history.Refresh()

        # Fetch the results of our HTTP Server.

        client_idents = http_server.ClientIdentifiersGet()
        if len(client_idents) == 0:
            print("Nothing connected")
            sys.exit(-1)

        client_identifier = client_idents[0]
        http_session = http_server.HttpSessionInfoGet(client_identifier)
        http_hist = http_session.ResultHistoryGet()
        http_hist.Refresh()

        # Now we have all results available in our API, we can process them.

        # We will store results in a list, containing dicts
        # { 'timestamp': ... , 'SSID': ... , 'BSSID': ... , 'throughput': ...
        results = []

        interval_snapshots = network_info_history.IntervalGet()
        for network_info_interval in interval_snapshots:
            # Find the corresponding HTTP snapshot
            timestamp = network_info_interval.TimestampGet()
            try:
                http_interval = http_hist.IntervalGetByTime(timestamp)
                # Get the average througput for this interval
                # type is byteblowerll.byteblower.DataRate
                rate = http_interval.AverageDataSpeedGet()

                rate_bps = rate.bitrate()

            except ConfigError as e:
                print("Couldn't fetch Throughput snapshot for timestamp", timestamp)
                print("Number of NetworkInfo snapshots:", len(interval_snapshots))
                print("Number of HTTP snapshots:", http_hist.IntervalLengthGet())
                print("ConfigError:", e.what())

                rate_bps = 0

            # Get the interfaces stored in this interval
            interfaces = network_info_interval.InterfaceGet()
            # Find the WiFi Interface
            network_interface = self.find_wifi_interface(interfaces)

            result = {
                'timestamp': timestamp,
                'throughput': int(rate_bps),

                # Default values
                'SSID': 'Unknown',
                'BSSID': 'Unknown',
                'RSSI': -127
            }

            if network_interface is None:
                print("WARNING: No WiFi interface found to query on timestamp",
                      timestamp)
            else:
                result.update({
                    'SSID': network_interface.WiFiSsidGet(),
                    'BSSID': network_interface.WiFiBssidGet(),
                    'RSSI': int(network_interface.WiFiRssiGet()),
                })

            results.append(result)

        self.server.PortDestroy(self.port)
        self.wireless_endpoint.Lock(False)
        return results

    def cleanup(self):
        instance = ByteBlower.InstanceGet()

        # Cleanup
        if self.meetingpoint is not None:
            instance.MeetingPointRemove(self.meetingpoint)
        if self.server is not None:
            instance.ServerRemove(self.server)

    def find_wifi_interface(self, interface_list):
        """"Looks for the wireless interface
        If wireless_interface is defined and not set to None, find this
        interface. If it is not found, look for the first interface with type
        NetworkInterfaceType_Wifi.  Otherwise, return None

        :param interface_list: List of interfaces to query
        :type interface_list: `byteblowerll.byteblower.NetworkInterfaceList`
        :return: the selected network interface
        :rtype: :class:`byteblowerll.byteblower.NetworkInterface`
        """

        if self.wireless_interface is not None:
            for interface in interface_list:
                if (interface.DisplayNameGet() == self.wireless_interface
                        or interface.NameGet() == self.wireless_interface):
                    return interface

        # Still here?
        # no specific interface requested or the interface was not found, so
        # just selecting the first interface with an SSID.

        for interface in interface_list:
            if (interface.TypeGet() == NetworkInterfaceType.WiFi
                    and interface.WiFiSsidGet() != ''):
                return interface

        # still here?
        # no suitable interface found, returning None
        return None

    def select_wireless_endpoint_uuid(self):
        """
        Walk over all known devices on the meetingpoint.
        If the device has the status 'Available', return its UUID, otherwise
        return None.

        :return: a string representing the UUID or None
        :rtype: str
        """
        from byteblowerll.byteblower import DeviceStatus_Available

        for device in self.meetingpoint.DeviceListGet():
            # is the status Available?
            if device.StatusGet() == DeviceStatus_Available:
                # yes, return the UUID
                return device.DeviceIdentifierGet()

        # No device found, return None
        return None


def human_readable_date(bb_timestamp):
    return str(datetime.datetime.fromtimestamp(int(bb_timestamp / 1e9)))


def write_csv(result_list, filename, first_key, separator=';'):
    # We use the first item to collect our headers
    first_result = result_list[0]

    # Make sure the first key in the list is the key we want to be the first.
    keys = list(first_result.keys())
    keys.remove(first_key)
    keys.insert(0, first_key)

    with open(filename, 'w') as f:
        # Write the headers
        f.write(separator.join(['"' + key + '"' for key in keys]) + "\n")

        # Write the results
        for result in result_list:
            items = []

            # format the result items,
            # strings will be quoted,
            # timestamps will be human readable dates
            for key in keys:
                item = result[key]

                if key == 'timestamp':
                    item = human_readable_date(int(item))

                if isinstance(item, str):
                    item = '"' + item + '"'

                items.append(str(item))

            # Write the result
            f.write(separator.join(items) + "\n")


if __name__ == '__main__':
    example = Example(**configuration)
    device_name = "Unknown"
    try:
        example_results = example.run()
        device_name = example.wireless_endpoint.DeviceInfoGet().GivenNameGet()
    finally:
        example.cleanup()

    print("Storing the results")
    results_file = os.path.basename(__file__) + ".csv"
    write_csv(example_results, filename=results_file, first_key='timestamp')
    print("Results written to", results_file)

    plot_using_highcharts(device_name, example_results)

    sys.exit(0)
