"""
HTTP MultiServer/MultiClient for the ByteBlower Python API.
All examples are guaranteed to work with Python 2.7 and above

Copyright 2018, Excentis N.V.
"""
# Needed for python2 / python3 print function compatibility
from __future__ import print_function

# import the ByteBlower module
import byteblowerll.byteblower as byteblower

import time


configuration = {
    # Address (IP or FQDN) of the ByteBlower server to use
    'server_address': 'byteblower-tp-1300.lab.byteblower.excentis.com',

    # Configuration for the first ByteBlower port.
    # Will be used as HTTP server.
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

        # TCP port number to be used by the HTTP connection.
        # On the HTTP server, this will be the port on which the server
        # listens.
        'tcp_port': 4096
    },

    # Configuration for the second ByteBlower port.
    # Will be used as HTTP client.
    'port_2_config': {
        'interface': 'trunk-1-25',
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

        # TCP port range the HTTP Clients will use to connect with
        # the HTTP server
        'tcp_port_min': 32000,
        'tcp_port_max': 50000
    },

    # HTTP Method
    # HTTP Method can be GET or PUT
    # - GET: Standard HTTP download, we retrieve data from the web server
    # - PUT: Standard HTTP upload, the wireless endpoint will push data to the
    #        webserver
    'http_method': 'GET',
    # 'http_method': 'PUT',

    # total duration, in nanoseconds.
    # This is the duration of the flow.  When this duration expires,
    # all sessions will be stopped.
    'duration': 10000000000,

    # session duration, in nanoseconds
    # Duration of the individual sessions
    # 'session_duration': 1500000000,
    'session_duration': None,

    # session size, in bytes
    # The number of bytes transmitted by a session
    'session_size': 1 * 1000 * 1000,
    # 'session_size': None,

    # max concurrent sessions
    # Maximum number of sessions that will be running simultaneously
    'max_concurrent_sessions': 100,

    # maximum number of sessions
    # No more than this number of sessions will be created
    # 0 means no limit
    'max_total_sessions': 0,

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
        self.session_duration = kwargs['session_duration']
        self.session_size = kwargs['session_size']
        self.max_concurrent_sessions = kwargs['max_concurrent_sessions']
        self.max_total_sessions = kwargs['max_total_sessions']
        self.tos = kwargs['tos']

        self.server = None
        self.port_1 = None
        self.port_2 = None

    def cleanup(self):
        """Clean up the created objects"""
        byteblower_instance = byteblower.ByteBlower.InstanceGet()
        if self.port_1:
            self.server.PortDestroy(self.port_1)
            self.port_1 = None

        if self.port_2:
            self.server.PortDestroy(self.port_2)
            self.port_2 = None

        if self.server is not None:
            byteblower_instance.ServerRemove(self.server)
            self.server = None

    def run(self):
        byteblower_instance = byteblower.ByteBlower.InstanceGet()

        print("Connecting to ByteBlower server %s..." % self.server_address)
        self.server = byteblower_instance.ServerAdd(self.server_address)

        # Create the port which will be the HTTP server (port_1)
        print("Creating HTTP Server port")
        self.port_1 = self.provision_port(self.port_1_config)

        print("Creating HTTP Client port")
        # Create the port which will be the HTTP client (port_2)
        self.port_2 = self.provision_port(self.port_2_config)

        http_server_ip_address = self.port_1_config['ip_address']

        # create a HTTP server
        http_server = self.port_1.ProtocolHttpMultiServerAdd()
        server_tcp_port = self.port_1_config['tcp_port']
        if server_tcp_port is not None:
            http_server.PortSet(server_tcp_port)
        else:
            server_tcp_port = http_server.PortGet()

        # create a HTTP Client
        http_client = self.port_2.ProtocolHttpMultiClientAdd()

        # - remote endpoint
        http_client.RemoteAddressSet(http_server_ip_address)
        http_client.RemotePortSet(server_tcp_port)

        # - local endpoint
        http_client.LocalPortRangeSet(self.port_2_config['tcp_port_min'],
                                      self.port_2_config['tcp_port_max'])

        # Configure the direction.
        # If the HTTP Method is GET,
        #   traffic will flow from the HTTP server to the HTTP client
        # If the HTTP Method is PUT,
        #   traffic will flow from the HTTP client to the HTTP server
        http_client.HttpMethodSet(self.http_method)

        print("Server port:", self.port_1.DescriptionGet())
        print("Client port:", self.port_2.DescriptionGet())

        # let the HTTP server listen for requests
        http_server.Start()

        # - total duration of all sessions
        http_client.DurationSet(self.duration)

        # - how many connections can be created?
        http_client.CumulativeConnectionLimitSet(self.max_total_sessions)

        # - how many connections can be running at the same time
        http_client.MaximumConcurrentRequestsSet(self.max_concurrent_sessions)

        # - individual duration, can be size-based or time-based
        if self.session_duration is not None:
            # let the HTTP Client request a page of a specific duration
            # to download...
            http_client.SessionDurationSet(self.session_duration)
        elif self.session_size is not None:
            # let the HTTP Client request a page of a specific size...
            http_client.SessionSizeSet(self.session_size)
        else:
            raise ValueError("Either duration or request_size must be configured")

        print("Starting the HTTP client")
        http_client.Start()

        http_client_result = http_client.ResultGet()

        for iteration in range(10):
            time.sleep(1)

            http_client_result.Refresh()
            print("-" * 10)
            print("Iteration", iteration+1)
            print("    connections attempted", http_client_result.ConnectionsAttemptedGet())
            print("    connections established", http_client_result.ConnectionsEstablishedGet())
            print("    connections aborted", http_client_result.ConnectionsAbortedGet())
            print("    connections refused", http_client_result.ConnectionsRefusedGet())

        print("-" * 10)

        http_client.Stop()
        http_server.Stop()
        print("Stopped the HTTP client")

        request_status_value = http_client.StatusGet()
        request_status_string = byteblower.ConvertHTTPMultiClientStatusToString(request_status_value)

        http_client_result.Refresh()

        tx_bytes = http_client_result.TcpTxByteCountGet()
        tx_speed = http_client_result.TcpTxSpeedGet()
        rx_bytes = http_client_result.TcpRxByteCountGet()
        rx_speed = http_client_result.TcpRxSpeedGet()

        http_server_result = http_server.ResultGet()
        http_server_result.Refresh()

        print("Requested Duration : {} nanoseconds".format(self.duration))
        print("Status             : {}".format(request_status_string))
        print("Client Result data : {}".format(http_client_result.DescriptionGet()))
        print("Server Result data : {}".format(http_server_result.DescriptionGet()))

        return [
            self.duration,
            self.session_duration,
            self.session_size,
            self.max_total_sessions,
            self.max_concurrent_sessions,
            tx_bytes, rx_bytes,
            tx_speed, rx_speed,
            request_status_value
        ]

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
    example = Example(**configuration)
    try:
        example.run()
    finally:
        example.cleanup()
