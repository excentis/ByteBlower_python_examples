from __future__ import print_function

import datetime
import sys
import time

from byteblowerll.byteblower import ByteBlower, ConfigError
from byteblowerll.byteblower import ParseHTTPRequestMethodFromString
from byteblowerll.byteblower import WirelessEndpointList, DeviceStatus

configuration = {
    # Address (IP or FQDN) of the ByteBlower server to use
    'server_address': 'byteblower-tp-2100.lab.byteblower.excentis.com',

    # Interface on the server to create a port on.
    'server_interface': 'trunk-1-13',

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
    # 'meetingpoint_address': None,

    # UUIDs of the ByteBlower WirelessEndpoint to use.  This wireless endpoints
    # *must* be registered to the meetingpoint  configured by
    # meetingpoint_address.
    # Special value: None.  When the UUID is set to None, the example will
    #                       automatically select all available wireless
    #                       endpoints.
    'wireless_endpoint_uuid_list': [],
    # 'wireless_endpoint_uuid_list': ['6d9c2347-e6c1-4eea-932e-053801de32eb', ],

    # TCP port for the HTTP server
    # Special value: None: the server will select one automatically
    'port_tcp_port': None,

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
        self.server_address = kwargs.pop('server_address')
        self.server_interface = kwargs.pop('server_interface')
        self.port_mac_address = kwargs.pop('port_mac_address')
        self.port_ip_address = kwargs.pop('port_ip_address')

        self.meetingpoint_address = kwargs.pop('meetingpoint_address',
                                               self.server_address)
        if self.meetingpoint_address is None:
            self.meetingpoint_address = self.server_address

        self.wireless_endpoint_uuids = kwargs.pop('wireless_endpoint_uuids',
                                                  [])
        self.port_tcp_port = kwargs.pop('port_tcp_port', 80)

        http_method = kwargs.pop('http_method', 'GET')
        self.http_method = ParseHTTPRequestMethodFromString(http_method)
        self.duration = kwargs.pop('duration', 10000000000)
        self.tos = kwargs.pop('tos', 0)

        self.server = None
        self.port = None
        self.meetingpoint = None
        self.wireless_endpoints = []

    def __setup_byteblower_port(self):
        instance = ByteBlower.InstanceGet()
        assert isinstance(instance, ByteBlower)

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

    def __setup_http_server(self):
        # Configure the HTTP server, running on the ByteBlower port.
        http_server = self.port.ProtocolHttpServerAdd()

        # Configure the TCP port on which the HTTP server wll listen
        if self.port_tcp_port is not None:
            http_server.PortSet(self.port_tcp_port)

        # Configure the receive window.
        http_server.ReceiveWindowScalingEnable(True)
        http_server.ReceiveWindowScalingValueSet(7)

        # A HTTP server will not listen for new connections as long it is not
        # started.  You can compare it to e.g. Apache or nginx, it won't accept
        # new connections as long the daemon is not started.
        http_server.Start()

        print("HTTP server configuration:", http_server.DescriptionGet())

        return http_server

    def __setup_http_client(self, wireless_endpoint, http_server):
        # Configure the client.
        http_client = wireless_endpoint.ProtocolHttpClientAdd()
        # Configure the remote endpoint to which it must connect.
        # This is the IP address and port of the HTTP server configured above
        http_client.RemoteAddressSet(self.port.Layer3IPv4Get().IpGet())
        http_client.RemotePortSet(http_server.PortGet())

        http_client.RequestDurationSet(self.duration)
        http_client.RequestInitialTimeToWaitSet(0)
        # What will we do? HTTP Get or HTTP PUT?
        http_client.HttpMethodSet(self.http_method)

        http_client.TypeOfServiceSet(self.tos)
        print("HTTP client configuration:", http_client.DescriptionGet())

        return http_client

    def run(self):
        instance = ByteBlower.InstanceGet()
        assert isinstance(instance, ByteBlower)

        self.__setup_byteblower_port()

        http_server = self.__setup_http_server()

        # Connect to the meetingpoint
        self.meetingpoint = instance.MeetingPointAdd(self.meetingpoint_address)

        # Get the maximum of devices allowed by the license, so we can limit
        # the number of devices we lock.
        byteblower_license = self.meetingpoint.ServiceInfoGet().LicenseGet()
        max_devices_allowed = byteblower_license.NumberOfWirelessEndpointsGet()

        # If no WirelessEndpoint UUID was given, search an available one.
        if not self.wireless_endpoint_uuids:
            self.wireless_endpoint_uuids = self.select_wireless_endpoint_uuids()

        # Limit the number of wireless endpoints to the number we fetched earlier.
        if len(self.wireless_endpoint_uuids) > max_devices_allowed:
            first_devices = self.wireless_endpoint_uuids[:max_devices_allowed]
            self.wireless_endpoint_uuids = first_devices

        # Get the WirelessEndpoint devices
        self.wireless_endpoints = [self.meetingpoint.DeviceGet(uuid)
                                   for uuid in self.wireless_endpoint_uuids]

        print("Using wireless endpoints:")
        for wireless_endpoint in self.wireless_endpoints:
            print(wireless_endpoint.DescriptionGet())

        # Now we have the correct information to start configuring the flows.
        for wireless_endpoint in self.wireless_endpoints:
            # Claim the wireless endpoint for ourselves.  This means that
            #  nobody but us can use this device.
            print("Locking device", wireless_endpoint.DeviceIdentifierGet())
            try:
                wireless_endpoint.Lock(True)
            except ConfigError as e:
                print("Could not lock!", e.getMessage(), file=sys.stderr)
                raise

        for wireless_endpoint in self.wireless_endpoints:
            self.__setup_http_client(wireless_endpoint, http_server)

        # now the flows are configured and the HTTP server is listening,
        # start the wireless endpoints.

        # Add all the wireless endpoint into a WirelessEndpointList.
        # Our API currently doesn't allow passing a pure python-list.
        all_wireless_endpoints = WirelessEndpointList()
        for wireless_endpoint in self.wireless_endpoints:
            all_wireless_endpoints.append(wireless_endpoint)

        # Send the Scenario to all wireless endpoints
        # Sending the scenario per device would take at least the number of
        # Wireless Endpoints in seconds, since they beat only once per second.
        # Using this technique they get their scenario in the next 2 heartbeats.
        print("Preparing the devices")
        self.meetingpoint.DevicesPrepare(all_wireless_endpoints)

        # Now we will start the wireless endpoints at once.
        # As with prepare, sending the start using the meetingpoint is a lot
        # faster than starting them one by one.  In fact it is the only way
        # to get them started in a coordinated way.
        # The meetingpoint will return the timestamp when the devices will
        # start.
        starttime_ns = self.meetingpoint.DevicesStart(all_wireless_endpoints)
        now_ns = self.meetingpoint.TimestampGet()
        time_to_wait_ns = starttime_ns - now_ns
        time_to_wait = datetime.timedelta(microseconds=time_to_wait_ns / 1000)
        print("Waiting for", time_to_wait.total_seconds(),
              "seconds for the devices to start.")
        time.sleep(time_to_wait.total_seconds())

        print("Devices started.")

        # We need to wait for the devices to become available again
        # This indicates that the scenarios are finished.

        still_running = True
        while still_running:
            time.sleep(1)

            still_running = False
            running_devices = 0

            for wireless_endpoint in self.wireless_endpoints:
                allowed_statusses = [DeviceStatus.Reserved,
                                     DeviceStatus.Available
                                     ]

                # The wireless Endpoint is running a test when it is
                # - Armed
                # - Running
                # If the device is Available or Reserved (= Available + Locked)
                # the device is not running a test.
                if wireless_endpoint.StatusGet() not in allowed_statusses:
                    still_running = True
                    running_devices += 1

            print(running_devices, "running,",
                  len(http_server.ClientIdentifiersGet()), "clients connected")

        print("All devices finished.")

        # Wireless Endpoint has returned. Collect and process the results.

        # It was a new HTTP server. There will thus be only 1 client.
        client_idents = http_server.ClientIdentifiersGet()
        if len(client_idents) == 0:
            print("Nothing connected")
            sys.exit(-1)

        # save the results to CSV, this allows further analysis afterwards
        collected_results = self.collect_results(http_server)

        return collected_results

    def cleanup(self):
        instance = ByteBlower.InstanceGet()

        # Cleanup

        for wireless_endpoint in self.wireless_endpoints:
            wireless_endpoint.Lock(False)

        if self.meetingpoint is not None:
            instance.MeetingPointRemove(self.meetingpoint)

        if self.server is not None:
            instance.ServerRemove(self.server)

    def select_wireless_endpoint_uuids(self):
        """
        Walk over all known devices on the meetingpoint.
        If the device has the status 'Available', return its UUID,
        otherwise return None
        :return: a list of strings representing the UUIDs
        :rtype: list
        """
        devices = []

        for device in self.meetingpoint.DeviceListGet():
            # is the status Available?
            if device.StatusGet() == DeviceStatus.Available:
                # yes, return the UUID
                devices.append(device.DeviceIdentifierGet())

        # No device found, return None
        return devices

    @staticmethod
    def collect_result(http_session):
        history = http_session.ResultHistoryGet()
        history.Refresh()
        cumulative = history.CumulativeLatestGet()

        mbit_s = cumulative.AverageDataSpeedGet().MbpsGet()
        first = min([cumulative.RxTimestampFirstGet(),
                     cumulative.TxTimestampFirstGet()])
        last = max([cumulative.RxTimestampLastGet(),
                    cumulative.TxTimestampLastGet()])

        return {
            'throughput': mbit_s,
            'timestamp_first': first,
            'timestamp_last': last
        }

    def collect_results(self, http_server):
        """" Function that writes the results to CSV files.
        """
        results = {
            'session': [],
            'total': {
                'throughput': 0
            }
        }
        for session_id in http_server.ClientIdentifiersGet():
            session = http_server.HttpSessionInfoGet(session_id)

            session_result = self.collect_result(session)

            results['total']['throughput'] += session_result['throughput']
            results['session'].append(session_result)

        return results

    @staticmethod
    def bytes_per_sample_to_mbit_s(sample_duration, n_bytes):
        """
            Utility method for conversion.
            It converts bytes in a sample to Mbit/s.
        """
        return (n_bytes * 8 * 1e9) / (1e6 * sample_duration)


if __name__ == '__main__':
    from pprint import pprint

    example = Example(**configuration)
    try:
        pprint(example.run())
    finally:
        example.cleanup()
