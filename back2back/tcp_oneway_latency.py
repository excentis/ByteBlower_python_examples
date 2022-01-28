"""
Basic IPv4 TCP Example for the ByteBlower Python API.
All examples are guaranteed to work with Python 2.7 and above

This example show how to use TCP with ByteBlower. This all happens in the
run method of the Example class.

The ByteBlower port configuration is flexible, you can configure
 * IPv4 (static or DHCP)
 * IPv6 (static, SLAAC, or DHCP)
 * Optionally add a VLAN.
"""
# Needed for python2 / python3 print function compatibility
from __future__ import print_function

# import the ByteBlower module
import byteblowerll.byteblower as api

import time
import datetime

configuration = {
    # Address (IP or FQDN) of the ByteBlower server to use
    'server_address': '10.10.1.202',

    # Configuration for the first ByteBlower port.
    # Will be used as HTTP server.
    'port_1_config': {
        'interface': 'trunk-1-7',
        'mac': '00:bb:01:00:00:01',
        # IP configuration for the ByteBlower Port.
        # Options are 'DHCPv4', 'DHCPv6', 'SLAAC', 'static'
        # if DHCPv4, use "dhcpv4"
        'ip': 'dhcpv4',
        # if DHCPv6, use "dhcpv6"
        # 'ip': 'dhcpv6',
        # if SLAAC, use "slaac"
        # 'ip': 'slaac',
        # if staticv4, use ["ipaddress", netmask, gateway]
        # 'ip': ['192.168.0.2', "255.255.255.0", "192.168.0.1"],
        # if staticv6, use ["ipaddress", prefixlength]
        # 'ip': ['3000:3128::24', '64'],

        # Optionally you can define a VLAN.
        # 'vlan': 2,

        # TCP port number to be used by the HTTP connection.
        # On the HTTP server, this will be the port on which the
        # server listens.
        'tcp_port': 4096
    },

    # Configuration for the second ByteBlower port.
    # Will be used as HTTP client.
    'port_2_config': {
        'interface': 'trunk-1-3',
        'mac': '00:bb:01:00:00:02',

        # Optionally you can define a VLAN.
        # 'vlan': 2,

        # IP configuration for the ByteBlower Port.
        # Options are 'DHCPv4', 'DHCPv6', 'SLAAC', 'static'
        # if DHCPv4, use "dhcpv4"
        'ip': 'dhcpv4',
        # if DHCPv6, use "dhcpv6"
        # ip': 'dhcpv6',
        # if SLAAC, use "slaac"
        # 'ip': 'slaac',
        # if staticv4, use ["ipaddress", netmask, gateway]
        # 'ip': ['192.168.0.2', "255.255.255.0", "192.168.0.1"],
        # if staticv6, use ["ipaddress", prefixlength]
        # 'ip': ['3000:3128::24', '64'],

        # TCP port number to be used by the HTTP connection.
        # On the HTTP client, this will be the local port the client uses to
        # connect to the server.
        'tcp_port': 4096
    },

    # HTTP Method
    # HTTP Method can be GET or PUT
    # - GET: Standard HTTP download, we retrieve data from the web server
    # - PUT: Standard HTTP upload, the wireless endpoint will push data to the
    #        webserver
    'http_method': 'GET',
    # 'http_method': 'PUT',

    # duration, in nanoseconds
    # Duration of the session.  If None is given, the request_size will be used
    # 'duration': None,
    'duration': 5000000000,

    # The maximum duration in nanoseconds the session can take.
    # If it takes longer, the example will stop the session.
    # If omitted or None is given, the default of 1 minute will be used.
    # 'max_duration': 60000000000,

    # request size
    # Number of bytes to download/upload, if None is given, the duration will
    # be used
    'request_size': None,
    # 'request_size': 1000000,

    # TOS value to use on the HTTP client (and server)
    'tos': 0
}


class Example:
    def __init__(self, **kwargs):
        self.server_address = kwargs['server_address']
        self.port_1_config = kwargs['port_1_config']
        self.port_2_config = kwargs['port_2_config']

        # Helper function, we can use this to parse the HTTP Method to the
        # enumeration used by the API
        from byteblowerll.byteblower import ParseHTTPRequestMethodFromString
        http_method_arg = kwargs['http_method']
        self.http_method = ParseHTTPRequestMethodFromString(http_method_arg)
        self.duration = kwargs['duration']
        self.request_size = kwargs['request_size']
        self.tos = kwargs['tos']

        # default duration limit
        default_max_duration = 1e9
        max_duration = kwargs.pop('max_duration', default_max_duration)
        max_duration = max_duration if max_duration else default_max_duration

        self.max_duration = datetime.timedelta(seconds=int(max_duration) / 1e9)

        self.server = None
        self.port_1 = None
        self.port_2 = None

    def cleanup(self):
        byteblower_instance = api.ByteBlower.InstanceGet()
        if self.server is not None:
            byteblower_instance.ServerRemove(self.server)
            self.server = None

    def check_server_version(self):
        server_version = self.server.ServiceInfoGet().VersionGet()
        version_components = tuple([int(i) for i in server_version.split('.')])
        print("Server runs version %s" % server_version)

        if version_components < (2, 14, 0):
            raise RuntimeError(
                "The server on %s seems to be too old to support this feature.  "
                "Expecting version %s, but it runs %s:" % (
                    self.server_address, "2.14.0", server_version
                ))

    def run(self):
        byteblower_instance = api.ByteBlower.InstanceGet()

        print("Connecting to ByteBlower server %s..." % self.server_address)
        self.server = byteblower_instance.ServerAdd(self.server_address)

        # The TCP OneWay Latency feature was only added in ByteBlower 2.14,
        # so we cannot run this example if the server is too old.
        # Check for it first.
        self.check_server_version()

        # Create the port which will be the HTTP server (port_1)
        print("Creating HTTP Server port")
        self.port_1 = self.provision_port(self.port_1_config)

        print("Creating HTTP Client port")
        # Create the port which will be the HTTP client (port_2)
        self.port_2 = self.provision_port(self.port_2_config)

        http_server_ip_address = self.port_1_config['ip_address']

        # create an HTTP server
        http_server = self.port_1.ProtocolHttpServerAdd()  # type: api.HTTPServer
        server_tcp_port = self.port_1_config['tcp_port']
        if server_tcp_port is not None:
            http_server.PortSet(server_tcp_port)
        else:
            server_tcp_port = http_server.PortGet()

        # create an HTTP Client
        http_client = self.port_2.ProtocolHttpClientAdd()  # type: api.HTTPClient

        # - remote endpoint
        http_client.RemoteAddressSet(http_server_ip_address)
        http_client.RemotePortSet(server_tcp_port)

        # Configure the direction.
        # If the HTTP Method is GET,
        #     traffic will flow from the HTTP server to the HTTP client
        # If the HTTP Method is PUT,
        #     traffic will flow from the HTTP client to the HTTP server
        http_client.HttpMethodSet(self.http_method)

        # Request the ByteBlower to measure latency
        http_client.LatencyEnable(True)

        if self.duration is not None:
            # let the HTTP Client request a page of a specific duration to
            # download...
            http_client.RequestDurationSet(self.duration)
        elif self.request_size is not None:
            # let the HTTP Client request a page of a specific size...
            http_client.RequestSizeSet(self.request_size)
        else:
            raise ValueError("Either duration or request_size must be configured")

        print("Server port:", self.port_1.DescriptionGet())
        print("Client port:", self.port_2.DescriptionGet())

        # let the HTTP server listen for requests
        print("Starting the HTTP Server")
        http_server.Start()

        print("Starting the HTTP request")
        http_client.RequestStart()
        start_time = datetime.datetime.now()

        # Wait until the HTTP Client is connected with the HTTP server for a
        # maximum of 2 seconds
        # When the HTTP Client connects earlier than this duration, it will
        # return, otherwise it will throw an error.
        http_client.WaitUntilConnected(2 * 1000000000)

        client_session_info = http_client.HttpSessionInfoGet()  # type: api.HTTPSessionInfo

        client_session_info.Refresh()
        if client_session_info.RequestStatusGet() not in [
            api.HTTPRequestStatus.Running,
            api.HTTPRequestStatus.Error,
            api.HTTPRequestStatus.Finished
        ]:
            raise RuntimeError("HTTP Client not connected!")

        print("HTTP Client connected")

        http_server_session_info = http_server.HttpSessionInfoGet(http_client.ServerClientIdGet())

        while (
                datetime.datetime.now() - start_time < self.max_duration
                or client_session_info.RequestStatusGet() != api.HTTPRequestStatus.Finished
        ):
            # Refresh all results
            client_session_info.Refresh()
            http_server_session_info.Refresh()

            # The histories
            # The Result Histories contain the data over time.  This is useful
            # when intermediate intervals are needed
            client_session_info.ResultHistoryGet().Refresh()
            http_server_session_info.ResultHistoryGet().Refresh()

            # wait 1 second to repeat the loop
            time.sleep(1)

        http_client.RequestStop()
        http_server.Stop()

        return self.process_results(http_server, http_client)

    def process_results(self, server, client):
        # type: (api.HTTPServer, api.HTTPClient) -> dict

        server_session = server.HttpSessionInfoGet(client.ServerClientIdGet())
        client_session = client.HttpSessionInfoGet()

        # When the HTTP Request Method is "GET", the data will flow from
        # the server towards the client.
        # This is sometimes called "downstream"
        # When the HTTP Request Method is "PUT", the data will flow in the other
        # direction, thus from the client to the server.
        # This is sometimes called "upstream"

        tx_session_info = server_session
        rx_session_info = client_session

        if client.HttpMethodGet() == api.HTTPRequestMethod.Put:
            tx_session_info = client_session  # type: api.HTTPSessionInfo
            rx_session_info = server_session  # type: api.HTTPSessionInfo

        tx_result = tx_session_info.ResultGet()  # type: api.HTTPResultSnapshot
        rx_result = rx_session_info.ResultGet()  # type: api.HTTPResultSnapshot

        tx_tcp_session = tx_session_info.TcpSessionInfoGet()  # type: api.TCPSessionInfo
        rx_tcp_session = rx_session_info.TcpSessionInfoGet()  # type: api.TCPSessionInfo

        tx_tcp_result = tx_tcp_session.ResultGet()  # type: api.TCPResultSnapshot
        rx_tcp_result = rx_tcp_session.ResultGet()  # type: api.TCPResultSnapshot

        tx_average_data_speed = tx_result.AverageDataSpeedGet()  # type: api.DataRate
        rx_average_data_speed = rx_result.AverageDataSpeedGet()  # type: api.DataRate

        # fetch our history information
        # for now we only include the rx side information
        # - Average speed
        # - Latency info (min, avg, max, jitter)
        history_results = []
        rx_history = rx_session_info.ResultHistoryGet()  # type: api.HTTPResultHistory
        rx_history.Refresh()

        for interval_snapshot in rx_history.IntervalGet():  # type: api.HTTPResultData
            dataspeed = interval_snapshot.AverageDataSpeedGet()

            history_results.append({
                "timestamp_nanoseconds": interval_snapshot.TimestampGet(),
                "rx_throughput_bits_per_seconds": dataspeed.bitrate(),
                "rx_min_latency_nanoseconds": interval_snapshot.LatencyMinimumGet(0),
                "rx_avg_latency_nanoseconds": interval_snapshot.LatencyAverageGet(0),
                "rx_max_latency_nanoseconds": interval_snapshot.LatencyMaximumGet(0),
                "rx_jitter_nanoseconds": interval_snapshot.JitterGet(0),
            })

        return {
            "request_size_bytes": self.request_size,
            "request_duration_nanoseconds": self.duration,
            "tx_data_bytes": tx_tcp_result.TxByteCountTotalGet(),
            "rx_data_bytes": rx_tcp_result.RxByteCountTotalGet(),
            "tx_throughput_bits_per_second": tx_average_data_speed.bitrate(),
            "rx_throughput_bits_per_second": rx_average_data_speed.bitrate(),
            "rx_min_latency_nanoseconds": rx_result.LatencyMinimumGet(0),
            "rx_avg_latency_nanoseconds": rx_result.LatencyAverageGet(0),
            "rx_max_latency_nanoseconds": rx_result.LatencyMaximumGet(0),
            "rx_jitter_nanoseconds": rx_result.JitterGet(0),
            "interval_results": history_results
        }

    def provision_port(self, config):
        port = self.server.PortCreate(config['interface'])
        port_l2 = port.Layer2EthIISet()
        port_l2.MacSet(config['mac'])

        vlan_id = config.get('vlan', None)
        vlan_id = int(vlan_id) if vlan_id is not None else None
        if vlan_id:
            port_l25 = port.Layer25VlanAdd()
            port_l25.IDSet(vlan_id)

        ip_config = config['ip']
        if not isinstance(ip_config, list):
            # Config is not static, DHCP or slaac
            if ip_config.lower() == "dhcpv4":
                port_l3 = port.Layer3IPv4Set()
                port_l3.ProtocolDhcpGet().Perform()
                config['ip_address'] = port_l3.IpGet()

            elif ip_config.lower() == "dhcpv6":
                port_l3 = port.Layer3IPv6Set()
                port_l3.ProtocolDhcpGet().Perform()
                config['ip_address'] = port_l3.IpDhcpGet()
            elif ip_config.lower() == "slaac":
                port_l3 = port.Layer3IPv6Set()
                port_l3.StatelessAutoconfiguration()
                config['ip_address'] = port_l3.IpStatelessGet()
        else:
            # Static configuration
            if len(ip_config) == 3:
                # IPv4
                port_l3 = port.Layer3IPv4Set()
                port_l3.IpSet(ip_config[0])
                port_l3.NetmaskSet(ip_config[1])
                port_l3.GatewaySet(ip_config[2])
                config['ip_address'] = port_l3.IpGet()
            elif len(ip_config) == 2:
                port_l3 = port.Layer3IPv6Set()
                # IPv6
                address = ip_config[0]
                prefix_length = ip_config[1]
                ip = "{}/{}".format(address, prefix_length)
                port_l3.IpManualAdd(ip)
                config['ip_address'] = ip_config[0]

        if not isinstance(config['ip_address'], str):
            ip = config['ip_address'][0]
            if '/' in ip:
                config['ip_address'] = ip.split('/')[0]

        print("Created port", port.DescriptionGet())
        return port


# When this python module is called stand-alone, the run-function must be
# called.  This approach makes it possible to include it in a series of
# examples.
if __name__ == "__main__":
    from pprint import pprint
    example = Example(**configuration)
    try:
        outcome = example.run()
        pprint(outcome)
    except api.ConfigError as e:
        print(e.what())
    finally:
        example.cleanup()
