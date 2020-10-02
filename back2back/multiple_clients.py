"""
This ByteBlower API example shows how to use several HTTPClients together.
We will show that you can easily use multiple HTTPClients and with the same 
HTTPServer.

This example assumes that you already familiar with 
the basic ByteBlower API for HTTP/TCP traffic. 
As you will notice, adding more TCP clients is easy!
"""

# Needed for python2 / python3 print function compatibility
from __future__ import print_function

import time

# import the ByteBlower module
from byteblowerll.byteblower import ByteBlower, RequestStartType
from byteblowerll.byteblower import ConvertHTTPRequestStatusToString
from byteblowerll.byteblower import HTTPRequestMethod, HTTPRequestStatus
from byteblowerll.byteblower import ParseHTTPRequestMethodFromString

configuration = {
    # Address (IP or FQDN) of the ByteBlower server to use
    'server_address': 'byteblower-tp-1300.lab.byteblower.excentis.com',

    # Configuration for the first ByteBlower port.  Will be used as HTTP server.
    'server_bb_port': {
        'interface': 'trunk-1-20',
        'mac': '00:bb:01:00:00:01',
        'ip': 'dhcpv4',

        # The TCP Server listens new connections on this Port number.
        'tcp_listen_port': 4096
    },

    # Configuration for the second ByteBlower port. On this ByteBlower port 
    # we will configure the HTTP clients.
    'client_bb_port': {
        'interface': 'trunk-1-14',
        'mac': '00:bb:01:00:00:02',

        'ip': 'dhcpv4',
    },

    # A list of HTTP clients. These will all start on on the client
    # ByteBlower Port.
    # Each HTTP Client has a:
    #     - http_method, this controls the direction of the traffic.
    #     - the duration, this is one of available stop conditions of a
    #       HTTP Server.
    #
    # Each client is time based, hence the duration parameter. Just as for the
    # basic TCP example, this parameter uses nano-seconds as unit.
    'http_clients': [
        {'http_method': 'GET',
         'duration': 5000000000},
        {'http_method': 'PUT',
         'duration': 15000000000},
        {'http_method': 'PUT',
         'duration': 10000000000},
    ]
}


class Example:
    def __init__(self, **kwargs):
        self.server_address = kwargs['server_address']
        self.server_bb_port_config = kwargs['server_bb_port']
        self.client_bb_port_config = kwargs['client_bb_port']

        self.http_client_configs = []
        for a_client in kwargs['http_clients']:
            config_http_method = a_client['http_method']
            config_duration = a_client['duration']
            http_method = ParseHTTPRequestMethodFromString(config_http_method)
            self.http_client_configs.append({
                'http_method': http_method,
                'duration': config_duration
            })

        self.server = None
        self.server_bb_port = None
        self.client_bb_port = None

    def run(self):
        byteblower_instance = ByteBlower.InstanceGet()

        print("Connecting to ByteBlower server %s..." % self.server_address)
        self.server = byteblower_instance.ServerAdd(self.server_address)

        # Create the port which will be the HTTP server (port_1)
        print("Creating HTTP Server port")
        self.server_bb_port = self.provision_port(self.server_bb_port_config)

        print("Creating HTTP Client port")
        # Create the port which will be the HTTP client (port_2)
        self.client_bb_port = self.provision_port(self.client_bb_port_config)

        http_server_ip_address = self.server_bb_port_config['ip_address']

        # create a HTTP server
        http_server = self.server_bb_port.ProtocolHttpServerAdd()
        server_tcp_port = self.server_bb_port_config['tcp_listen_port']
        http_server.PortSet(server_tcp_port)

        # The HTTP Server still needs to be started explicitly. 
        # You'll notice a difference for the HTTP Clients.
        http_server.Start()

        # This section differs from the basic TCP example.
        # We will create multiple clients onto the same the ByteBlowerPort.
        http_clients = []

        # We'll use the max_duration for the stop condition further in
        # the script.
        max_duration = 0

        # Configure each client one-by-one.
        # This part is the same as the basic TCP example.
        for client_config in self.http_client_configs:
            # create a new HTTP Client and configure it.
            # This part is the same for 1 or multiple ones.
            #
            # You can configure multiple clients to connect to the
            # the same server. You can even mix different HTTP Methods.
            http_client = self.client_bb_port.ProtocolHttpClientAdd()

            http_client.RemoteAddressSet(http_server_ip_address)
            http_client.RemotePortSet(server_tcp_port)

            http_client.HttpMethodSet(client_config['http_method'])
            http_client.RequestDurationSet(client_config['duration'])

            # The client configured duration is in nanoseconds, we want to keep
            # the max_duration as simple as 'seconds', so convert the value.
            client_duration_s = client_config['duration'] / 1e9
            max_duration = max(max_duration, client_duration_s)

            # The RequestStartType is the main configuration difference 
            # Between 2 TCP clients and multiple ones. Rather than starting
            # the client directly, we'll schedule when to start.
            http_client.RequestStartTypeSet(RequestStartType.Scheduled)
            http_clients.append(http_client)

        print("Server port:", self.server_bb_port.DescriptionGet())
        print("Client port:", self.client_bb_port.DescriptionGet())

        # This is another difference with the basic TCP example.
        # The Start method on a ByteBlower Port starts all scheduled traffic
        # types.  This example this means all configured HTTPClients.
        self.client_bb_port.Start()

        # Unlike before we now have several HTTPClients running together.
        # This makes determining when the scenario is finished more 
        # complex.
        # Below we show two different stop conditions:
        #    1. a time based one. (required)
        #    2. a client based one. (optional)
        #
        # Always use the time stop-condition. This provides a guaranteed
        # end in case when the flows can't connect. 
        #
        # A little bit of extra_time gives the HTTPClients some time extra
        # to make the actual connection.
        extra_time = 2
        start_moment = time.time()
        time_elapsed = 0
        while time_elapsed <= (extra_time + max_duration):
            time.sleep(1)

            time_elapsed = time.time() - start_moment
            print('%.2fs :: Waiting for clients to finish.' % time_elapsed)

            # Below is the second type of stop condition, a client based one.
            any_client_running = False

            # Consider a client finished when the state is either:
            # - Finished
            # - Error
            finished_states = [
                HTTPRequestStatus.Error,
                HTTPRequestStatus.Finished
            ]

            for http_client in http_clients:
                # Update the local API object with the  with the info on the
                # ByteBlowerServer.
                http_client.Refresh()

                # Check the status.
                status = http_client.RequestStatusGet()
                this_client_running = status not in finished_states
                any_client_running = any_client_running or this_client_running

            # all clients finished?  No need to wait any longer.
            if not any_client_running:
                break

        # Stop the HTTP Server. 
        # This step is optional but has the advantage of stopping traffic
        # to/from the HTTP Clients
        http_server.Stop()

        server_number_of_clients = len(http_server.ClientIdentifiersGet())

        print("")
        print("HTTP Server info     ")
        print("-" * 10)

        print("Connected clients     : {} ".format(server_number_of_clients))
        print("")

        print("HTTP Client info     ")
        print("-" * 10)

        # Process each of the clients.
        results = []
        for client in http_clients:
            results.append(self.process_http_client(client))

        return results

    def cleanup(self):
        if self.client_bb_port:
            self.server.PortDestroy(self.client_bb_port)
            self.client_bb_port = None
        if self.server_bb_port:
            self.server.PortDestroy(self.server_bb_port)
            self.server_bb_port = None

        # Disconnect from the ByteBlower server
        if self.server:
            ByteBlower.InstanceGet().ServerRemove(self.server)
            self.server = None

    @classmethod
    def process_http_client(cls, http_client):
        """
            This method processes all results from an HTTPClient.
            The method is very similar to the one in the TCP example.
        """
        named_http_methods = {HTTPRequestMethod.Put: 'PUT',
                              HTTPRequestMethod.Get: 'GET'}
        local_tcp_port = http_client.LocalPortGet()
        http_method = http_client.HttpMethodGet()
        http_method_string = named_http_methods[http_method]
        requested_duration = http_client.RequestDurationGet()

        print("Local TCP Port     : {} ".format(local_tcp_port))
        print("Direction          : {} ".format(http_method_string))
        print("Requested Duration : {} nanoseconds".format(requested_duration))

        request_status_value = http_client.RequestStatusGet()

        status = ConvertHTTPRequestStatusToString(request_status_value)
        if not http_client.HasSession():
            print("Status                : {}".format(status))
            print("")

        # The HTTPSession has all the OSI Layer 5 info.
        http_client_session_info = http_client.HttpSessionInfoGet()
        # Retrieve the latest info from the Server.
        http_client_session_info.Refresh()

        http_session_info = http_client.HttpSessionInfoGet()
        http_result = http_session_info.ResultGet()
        http_result.Refresh()

        tx_bytes = http_result.TxByteCountTotalGet()
        rx_bytes = http_result.RxByteCountTotalGet()
        avg_throughput = http_result.AverageDataSpeedGet()

        # The TCP Session has all the OSI Layer 4 information.
        tcp_result = http_session_info.TcpSessionInfoGet().ResultGet()
        tcp_result.Refresh()

        min_congestion = tcp_result.CongestionWindowMinimumGet()
        max_congestion = tcp_result.CongestionWindowMaximumGet()
        from byteblowerll.byteblower import DataRate
        assert isinstance(avg_throughput, DataRate)

        print("TX Payload            : {} bytes".format(tx_bytes))
        print("RX Payload            : {} bytes".format(rx_bytes))
        print("Average Throughput    : {}".format(avg_throughput.toString()))
        print("Min Congestion Window : {} bytes".format(min_congestion))
        print("Max Congestion Window : {} bytes".format(max_congestion))
        print("Status                : {}".format(status))
        print("")

        return [
            tx_bytes, rx_bytes, avg_throughput.bitrate(),
            min_congestion, max_congestion, request_status_value
        ]

    def provision_port(self, config):
        port = self.server.PortCreate(config['interface'])
        port_l2 = port.Layer2EthIISet()
        port_l2.MacSet(config['mac'])

        if 'vlan' in config:
            vlan_id = int(config['vlan'])
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
    example = Example(**configuration)
    try:
        example.run()
    finally:
        example.cleanup()
