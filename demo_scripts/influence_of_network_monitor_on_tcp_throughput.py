""""


"""
from __future__ import print_function
import time
import random
import datetime

from byteblowerll.byteblower import ByteBlower, DeviceStatus, ConfigError
import os
import sys

configuration = {
    # Address (IP or FQDN) of the ByteBlower server to use
    'server_address': '10.10.1.202',

    # Interface on the server to create a port on.
    'server_interface': 'trunk-1-1',

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
    'wireless_endpoint_uuid': None,
    # 'wireless_endpoint_uuid': '37cea3f2-79a8-4fc3-8f6d-2736fcce3313',

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
    'duration': 60 * 1000 * 1000 * 1000,

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

        # Number of samples per second
        self.sample_resolution = 1
        # duration of the samples taken. (nanoseconds)
        self.sample_duration = int(1000000000 / self.sample_resolution)

        # number of samples to take:
        # ( test_duration / sample_duration) is just enough, so we are doubling
        # this so we have more than enough
        self.sample_count = int(2 * (self.duration / self.sample_duration))

        self.server = None
        self.port = None
        self.meetingpoint = None
        self.wireless_endpoint = None
        self.network_info_monitor = None

    def __enter__(self):
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

        return self

    def __exit__(self, *args, **kwargs):
        instance = ByteBlower.InstanceGet()

        if self.wireless_endpoint is not None:
            self.wireless_endpoint.Lock(False)

        if self.meetingpoint is not None:
            instance.MeetingPointRemove(self.meetingpoint)
            self.meetingpoint = None

        if self.port is not None:
            self.server.PortDestroy(self.port)
            self.port = None

        if self.server is not None:
            instance.ServerRemove(self.server)
            self.server = None

    def _run_scenario(self):
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
            print(str(now), ":: Running for", str(now - start_moment))

        # Wireless Endpoint has returned. Collect and process the results.

        # Fetch the results from the wireless endpoint, they will be stored
        # at the MeetingPoint, we will fetch the results in a following step.
        self.wireless_endpoint.ResultGet()

    def _create_http_server(self):
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
        http_server.HistorySamplingIntervalDurationSet(self.sample_duration)
        http_server.HistorySamplingBufferLengthSet(self.sample_count)

        # A HTTP server will not listen for new connections as long it is not
        # started.  You can compare it to e.g. Apache or nginx, it won't accept
        # new connections as long the daemon is not started.
        http_server.Start()

        return http_server

    def _create_http_client(self):
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
        return http_client

    def run_without_monitor(self):
        http_server = self._create_http_server()
        print("HTTP server configuration:", http_server.DescriptionGet())

        http_client = self._create_http_client()

        print("HTTP client configuration:", http_client.DescriptionGet())

        # Run the configured scenario:
        self._run_scenario()

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

        for http_interval in http_hist.IntervalGet():
            timestamp = http_interval.TimestampGet()
            # Get the average througput for this interval
            # type is byteblowerll.byteblower.DataRate
            rate = http_interval.AverageDataSpeedGet()

            rate_bps = rate.bitrate()

            results.append({
                'timestamp': timestamp,
                'throughput': int(rate_bps),
            })

        return results

    def run_with_monitor(self):

        # Configure the HTTP server, running on the ByteBlower port.
        http_server = self._create_http_server()
        print("HTTP server configuration:", http_server.DescriptionGet())

        # Configure the client.
        http_client = self._create_http_client()
        print("HTTP client configuration:", http_client.DescriptionGet())

        self.network_info_monitor = self.wireless_endpoint.DeviceInfoGet().NetworkInfoMonitorAdd()
        self.network_info_monitor.ResultHistoryGet().SamplingIntervalDurationSet(self.sample_duration)
        print("NetworkInfo monitor configuration:", self.network_info_monitor.DescriptionGet())

        # Run the configured scenario
        self._run_scenario()

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

        for network_info_interval in network_info_history.IntervalGet():
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
                print("Number of NetworkInfo snapshots:", network_info_history.IntervalLengthGet())
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

        return results

    def run(self):
        results_without_monitor = self.run_without_monitor()
        results_with_monitor = self.run_with_monitor()

        return results_without_monitor, results_with_monitor

    def find_wifi_interface(self, interface_list):
        """"Looks for the wireless interface
        If wireless_interface is defined and not set to None, find this
        interface
        If it is not found, look for the first interface with type
        NetworkInterfaceType_Wifi.
        Else, return None

        :param interface_list: List of interfaces to query
        :type interface_list: `byteblowerll.byteblower.NetworkInterfaceList`
        :return: the selected network interface
        :rtype: :class:`byteblowerll.byteblower.NetworkInterface`
        """

        from byteblowerll.byteblower import (NetworkInterface,
                                             NetworkInterfaceType_WiFi)

        if self.wireless_interface is not None:
            for interface in interface_list:
                assert isinstance(interface, NetworkInterface)
                if (interface.DisplayNameGet() == self.wireless_interface
                        or interface.NameGet() == self.wireless_interface):
                    return interface

        # Still here?
        # no specific interface requested or the interface was not found, so
        # just selecting the first interface with an SSID.

        for interface in interface_list:
            if (interface.TypeGet() == NetworkInterfaceType_WiFi
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


def _get_max_throughput_mbps(*results):
    max_throughput = 0
    for resultset in results:
        for result in resultset:
            if 'throughput' in result:
                throughput = int(result['throughput'] / 1000000.0)
                max_throughput = max(throughput, max_throughput)
    return max_throughput


def _plot_throughput(throughput_axis, results, max_throughput):
    timestamps = []
    throughputs = []

    for item in results:
        timestamps.append(item['timestamp'] / 1000000000.0)
        throughputs.append(int(item['throughput'] / 1000000.0))

    min_timestamp = min(timestamps)
    timestamps = [x - min_timestamp for x in timestamps]

    throughput_axis.plot(timestamps, throughputs, 'b')
    throughput_axis.set_ylim(0, max_throughput)
    throughput_axis.set_xlabel('Time (s)')
    throughput_axis.set_ylabel('Throughput (Mbps)')

    throughput_axis.set_yticks(range(0, max_throughput, 100), minor=False)
    throughput_axis.grid(which='major', axis='y')


def _plot_rssi(rssi_axis, results):
    timestamps = []
    rssis = []

    for item in results:
        timestamps.append(item['timestamp'] / 1000000000.0)
        rssis.append(int(item['RSSI']))

    min_timestamp = min(timestamps)
    timestamps = [x - min_timestamp for x in timestamps]

    rssi_axis.plot(timestamps, rssis, 'r')
    rssi_axis.set_ylim(-127, 0)
    rssi_axis.set_xlabel('Time (s)')
    rssi_axis.set_ylabel('RSSI (dBm)')
    rssi_axis.set_yticks(range(-127, 0, 10), minor=False)


def plot_data(device_name, results_without_monitor, results_with_monitor):
    """
    Plots the data collected by the example using matplotlib
    :param device_name: Name of the device
    :param results_without_monitor: First data set returned by example
    :param results_with_monitor: Second data set returned by example
    """

    max_throughput = _get_max_throughput_mbps(results_with_monitor, results_without_monitor)

    # Get the default figure and axis
    fig, axes = plt.subplots(2, 1)

    fig_1_throughput_axis = axes[0]
    # Set the title of the graph
    fig_1_throughput_axis.set_title(device_name + " Throughput over time without monitor")
    _plot_throughput(fig_1_throughput_axis, results_without_monitor, max_throughput)

    fig_2_throughput_axis = axes[1]
    fig_2_throughput_axis.set_title(device_name + " Throughput over time with monitor")
    _plot_throughput(fig_2_throughput_axis, results_with_monitor, max_throughput)

    fig_2_rssi_axis = fig_2_throughput_axis.twinx()
    _plot_rssi(fig_2_rssi_axis, results_with_monitor)

    # Crop the image
    fig.tight_layout()
    # Save the image
    fig.savefig(os.path.basename(__file__) + ".png")


if __name__ == '__main__':
    # Do the magic, start with importing matplotlib
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    with Example(**configuration) as example:
        # Collect some information
        selected_device_name = example.wireless_endpoint.DeviceInfoGet().GivenNameGet()

        # Run the example
        result1 = example.run_without_monitor()

    with Example(**configuration) as example:
        # Run the example again
        result2 = example.run_with_monitor()

    plot_data(selected_device_name, result1, result2)

    sys.exit(0)
