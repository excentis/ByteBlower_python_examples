"""
Basic IPv4 Example for the ByteBlower Python API.
All examples are garanteed to work with Python 2.7 and above

Copyright 2018, Excentis N.V.
"""
# Needed for python2 / python3 print function compatibility
from __future__ import print_function

# import the ByteBlower module
import byteblowerll.byteblower as byteblower


configuration = {
    # Address (IP or FQDN) of the ByteBlower server to use
    'server_address': 'byteblower-tp-1300.lab.byteblower.excentis.com',

    # Configuration for the first ByteBlower port.  Will be used as HTTP server.
    'port_1_config': {
        'interface': 'trunk-1-13',
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

        # TCP port number to be used by the HTTP connection.  On the HTTP server,
        # this will be the port on which the server listens.
        'tcp_port': 4096
    },

    # Configuration for the second ByteBlower port.  Will be used as HTTP client.
    'port_2_config': {
        'interface': 'trunk-1-14',
        'mac': '00:bb:01:00:00:02',
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

        # TCP port number to be used by the HTTP connection.  On the HTTP client,
        # this will be the local port the client uses to connect to the server.
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
    'duration': None,
    # 'duration': 5000000000,


    # request size
    # Number of bytes to download/upload, if None is given, the duration will be used
    # 'request_size': None,
    'request_size': 1000000,

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

        self.http_method = ParseHTTPRequestMethodFromString(kwargs['http_method'])
        self.duration = kwargs['duration']
        self.request_size = kwargs['request_size']
        self.tos = kwargs['tos']

        self.server = None
        self.port_1 = None
        self.port_2 = None

    def run(self):
        byteblower_instance = byteblower.ByteBlower.InstanceGet()

        print("Connecting to ByteBlower server {}...".format(self.server_address))
        self.server = byteblower_instance.ServerAdd(self.server_address)

        # Create the port which will be the HTTP server (port_1)
        print("Creating HTTP Server port")
        self.port_1 = self.provision_port(self.port_1_config)

        print("Creating HTTP Client port")
        # Create the port which will be the HTTP client (port_2)
        self.port_2 = self.provision_port(self.port_2_config)

        http_server_ip_address = self.port_1_config['ip_address']

        # create a HTTP server
        http_server = self.port_1.ProtocolHttpServerAdd()
        server_tcp_port = self.port_1_config['tcp_port']
        if server_tcp_port is not None:
            http_server.PortSet(server_tcp_port)
        else:
            server_tcp_port = http_server.PortGet()

        # create a HTTP Client
        http_client = self.port_2.ProtocolHttpClientAdd()

        # - remote endpoint
        http_client.RemoteAddressSet(http_server_ip_address)
        http_client.RemotePortSet(server_tcp_port)

        # Configure the direction.
        # If the HTTP Method is GET, traffic will flow from the HTTP server to the HTTP client
        # If the HTTP Method is PUT, traffic will flow from the HTTP client to the HTTP server
        http_client.HttpMethodSet(self.http_method)

        print("Server port:", self.port_1.DescriptionGet())
        print("Client port:", self.port_2.DescriptionGet())

        # let the HTTP server listen for requests
        http_server.Start()

        if self.duration is not None:
            # let the HTTP Client request a page of a specific duration to download...
            http_client.RequestDurationSet(self.duration)
        elif self.request_size is not None:
            # let the HTTP Client request a page of a specific size...
            http_client.RequestSizeSet(self.request_size)
        else:
            raise ValueError("Either duration or request_size must be configured")

        print("Starting the HTTP request")
        http_client.RequestStart()

        # Wait until the HTTP Client is connected with the HTTP server for a
        # maximum of 2 seconds
        http_client.WaitUntilConnected(2 * 1000000000)

        # Wait until the HTTP Client has finished the "download"
        http_client.WaitUntilFinished(60 * 1000000000)

        http_client.RequestStop()
        http_server.Stop()

        http_client_session_info = http_client.HttpSessionInfoGet()
        http_client_session_info.Refresh()
        print("HTTP Client's Session Information:", http_client_session_info.DescriptionGet())

        request_status_value = http_client.RequestStatusGet()

        tx_bytes = 0
        rx_bytes = 0
        avg_throughput = 0
        min_congestion = 0
        max_congestion = 0

        if http_client_session_info.RequestMethodGet() == byteblower.HTTPRequestMethod_Get:
            http_session_info = http_client.HttpSessionInfoGet()
            http_result = http_session_info.ResultGet()
            http_result.Refresh()

            tx_bytes = http_result.TxByteCountTotalGet()
            rx_bytes = http_result.RxByteCountTotalGet()
            avg_throughput = http_result.AverageDataSpeedGet()

            tcp_result = http_session_info.TcpSessionInfoGet().ResultGet()
            tcp_result.Refresh()

            min_congestion = tcp_result.CongestionWindowMinimumGet()
            max_congestion = tcp_result.CongestionWindowMaximumGet()

        elif http_client_session_info.RequestMethodGet() == byteblower.HTTPRequestMethod_Get:
            http_session_info = http_server.HttpSessionInfoGet(http_client.ServerClientIdGet())
            http_result = http_session_info.ResultGet()
            http_result.Refresh()

            tx_bytes = http_result.TxByteCountTotalGet()
            rx_bytes = http_result.RxByteCountTotalGet()
            avg_throughput = http_result.AverageDataSpeedGet()

            tcp_result = http_session_info.TcpSessionInfoGet().ResultGet()
            tcp_result.Refresh()

            min_congestion = tcp_result.CongestionWindowMinimumGet()
            max_congestion = tcp_result.CongestionWindowMaximumGet()

        print("Requested Payload Size: {} bytes".format(self.request_size))
        print("Requested Duration    : {} nanoseconds".format(self.duration))
        print("TX Payload            : {} bytes".format(tx_bytes))
        print("RX Payload            : {} bytes".format(rx_bytes))
        print("Average Throughput    : {}".format(avg_throughput.toString()))
        print("Min Congestion Window : {} bytes".format(min_congestion))
        print("Max Congestion Window : {} bytes".format(max_congestion))
        print("Status                : {}".format(byteblower.ConvertHTTPRequestStatusToString(request_status_value)))

        return [self.request_size, self.duration,
                tx_bytes, rx_bytes, avg_throughput, min_congestion, max_congestion, request_status_value]

    def provision_port(self, config):
        port = self.server.PortCreate(config['interface'])
        port_l2 = port.Layer2EthIISet()
        port_l2.MacSet(config['mac'])

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
    Example(**configuration).run()
