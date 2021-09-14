from __future__ import print_function

import datetime
import json
import math
import random
import sys
import time

from byteblowerll import byteblower as api

configuration = {
    # Address (IP or FQDN) of the ByteBlower server to use
    'server_address': 'byteblower-dev-1300-1.lab.byteblower.excentis.com',

    # Interface on the server to create a port on.
    'server_interface': 'trunk-1-13',

    # MAC address of the ByteBlower port which will be generated
    'port_mac_address': '00:bb:01:00:00:01',

    # DHCP or IP configuration for the ByteBlower port
    # if DHCP, use "dhcp"
    'port_ip_address': 'dhcp',
    # if static, use ["ipaddress", "netmask", "gateway"]
    # 'port_ip_address': ['172.16.0.4', '255.255.252.0', '172.16.0.1'],

    # Address (IP or FQDN) of the ByteBlower MeetingPoint to use.  The wireless
    # endpoint *must* be registered on this meeting point.
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
    # 'wireless_endpoint_uuid': '6d9c2347-e6c1-4eea-932e-053801de32eb',

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
    'duration': 10000000000,

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
        self.port_tcp_port = kwargs['port_tcp_port']
        self.wireless_endpoint_tcp_port = kwargs['wireless_endpoint_tcp_port']

        # Helper function, we can use this to parse the HTTP Method to the
        # enumeration used by the API
        from byteblowerll.byteblower import ParseHTTPRequestMethodFromString

        method = kwargs['http_method']
        self.http_method = ParseHTTPRequestMethodFromString(method)
        self.duration = kwargs['duration']
        self.tos = kwargs['tos']

        self.server = None
        self.port = None
        self.meetingpoint = None
        self.wireless_endpoint = None

    def run(self):
        # duration of the samples taken. (nanoseconds)
        sample_duration = 100000000

        # number of samples to take:
        # ( test_duration / sample_duration) is just enough, so we are doubling
        # this so we have more than enough
        sample_count = int(math.ceil(2 * (self.duration / sample_duration)))

        instance = api.ByteBlower.InstanceGet()
        assert isinstance(instance, api.ByteBlower)

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

        try:
            self.wireless_endpoint.Prepare()
            self.wireless_endpoint.Start()
        except Exception as e:
            print("Error couldn't start the WE")
            print(str(e))
            sys.exit(-1)

        # Wait until the device returns.
        # As long the device is running, the device will be in
        # - DeviceStatus_Starting
        # - DeviceStatus_Running
        # As soon the device has finished the test, it will return to
        # 'DeviceStatus_Reserved', since we have a Lock on the device.
        status = self.wireless_endpoint.StatusGet()
        start_moment = datetime.datetime.now()
        while status != api.DeviceStatus.Reserved:
            time.sleep(1)
            status = self.wireless_endpoint.StatusGet()
            now = datetime.datetime.now()
            print(str(now), ":: Running for", str(now - start_moment), "::",
                  http_server.ClientIdentifiersGet().size(),
                  "client(s) connected")

        # Wireless Endpoint has returned. Collect and process the results.

        # It was a new HTTP server. There will thus be only 1 client.
        client_idents = http_server.ClientIdentifiersGet()
        if len(client_idents) == 0:
            print("Nothing connected")
            sys.exit(-1)

        first = client_idents[0]

        http_session = http_server.HttpSessionInfoGet(first)
        http_hist = http_session.ResultHistoryGet()

        http_hist.Refresh()

        # save the results to CSV, this allows further analysis afterwards
        collected_results = self.collect_results(http_session)

        cumulative_result = http_hist.CumulativeLatestGet()
        mbit_s = cumulative_result.AverageDataSpeedGet().MbpsGet()

        print("Average throughput", mbit_s, "Mbps")

        print("Removing the server")
        self.port.ProtocolHttpServerRemove(http_server)
        print("Removing the client")
        self.wireless_endpoint.ProtocolHttpClientRemove(http_client)

        # Cleanup
        self.server.PortDestroy(self.port)
        self.wireless_endpoint.Lock(False)
        return collected_results

    def cleanup(self):
        instance = api.ByteBlower.InstanceGet()

        # Cleanup
        if self.meetingpoint is not None:
            instance.MeetingPointRemove(self.meetingpoint)
        if self.server is not None:
            instance.ServerRemove(self.server)

    def select_wireless_endpoint_uuid(self):
        """
        Walk over all known devices on the meetingpoint.
        If the device has the status 'Available', return its UUID,
        otherwise return None
        :return: a string representing the UUID or None
        """

        for device in self.meetingpoint.DeviceListGet():
            # is the status Available?
            if device.StatusGet() == api.DeviceStatus.Available:
                # yes, return the UUID
                return device.DeviceIdentifierGet()

        # No device found, return None
        return None

    def collect_results(self, http_session):
        """" Function that writes the results to CSV files.
        """

        tcp_session = http_session.TcpSessionInfoGet()
        tcp_history = tcp_session.ResultHistoryGet()

        samples = []

        for tcp_sample in tcp_history.IntervalGet():  # type: api.TCPResultData
            sample_timestamp = tcp_sample.TimestampGet()
            samples.append({
                'timestamp': sample_timestamp,
                'tcp_tx_bytes': tcp_sample.TxByteCountTotalGet(),
                'tcp_rx_bytes': tcp_sample.RxByteCountTotalGet(),
                'tcp_roundtriptime_min': tcp_sample.RoundTripTimeMinimumGet(),
                'tcp_roundtriptime_max': tcp_sample.RoundTripTimeMaximumGet(),
                'tcp_roundtriptime_current': tcp_sample.RoundTripTimeCurrentGet(),
                'tcp_congestionwindow_current': tcp_sample.CongestionWindowCurrentGet(),
            })

        return {
            'we': {
                'uuid': self.wireless_endpoint.DeviceIdentifierGet(),
                'givenname': self.wireless_endpoint.DeviceInfoGet().GivenNameGet()
            },
            'samples': samples
        }

    @staticmethod
    def bytes_per_sample_to_mbit_s(sample_duration, n_bytes):
        """
            Utility method for conversion.
            It converts bytes in a sample to Mbit/s.
        """
        return (n_bytes * 8 * 1e9) / (1e6 * sample_duration)


def human_readable_date(bb_timestamp):
    return str(datetime.datetime.fromtimestamp(bb_timestamp / 1e9))


def make_csv_line(we_uuid, we_name, *items):
    all_itemslist = [we_uuid, we_name] + list(items)
    all_items = map(str, all_itemslist)
    return (", ".join(all_items)) + "\n"


if __name__ == '__main__':
    example = Example(**configuration)
    try:
        results = example.run()
    finally:
        example.cleanup()

    with open('ipv4_tcp_history.json', 'w') as handle:
        json.dump(results, handle, indent=4)
