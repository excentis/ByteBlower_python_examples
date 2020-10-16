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

import time, statistics, sys, json, datetime

# import the ByteBlower module
from byteblowerll.byteblower import ByteBlower, RequestStartType
from byteblowerll.byteblower import ConvertHTTPRequestStatusToString
from byteblowerll.byteblower import HTTPRequestMethod, HTTPRequestStatus
from byteblowerll.byteblower import ParseHTTPRequestMethodFromString

configuration = {
    # Address (IP or FQDN) of the ByteBlower server to use
    'server_address': 'byteblower-tutorial-3100.lab.byteblower.excentis.com',

    # Configuration for the first ByteBlower port.  Will be used as HTTP server.
    'server_bb_port': {
        'interface': 'nontrunk-1',
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


        # The TCP Server listens new connections on this Port number.
        'tcp_listen_port': 4096
    },

    # Configuration for the second ByteBlower port. On this ByteBlower port 
    # we will configure the HTTP clients.
    'client_bb_port': {
        'interface': 'trunk-1-50',
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

    },
}

upload = {
    'testname': 'upload_no_load',
    'http_clients': [
        {'http_method': 'PUT', 'duration': 2000000000, 'initial_wait_time': 1000000000, 'rate_limit': 10000, 'is_load': False},
        {'http_method': 'PUT', 'duration': 2000000000, 'initial_wait_time': 1000000000, 'rate_limit': 10000, 'is_load': False},
        {'http_method': 'PUT', 'duration': 2000000000, 'initial_wait_time': 1000000000, 'rate_limit': 10000, 'is_load': False},
        {'http_method': 'PUT', 'duration': 2000000000, 'initial_wait_time': 1000000000, 'rate_limit': 10000, 'is_load': False},
    ],
}

upload_with_load = {
    'testname': 'upload_with_load',
    'http_clients': [
        {'http_method': 'GET', 'duration': 10000000000, 'initial_wait_time': 0, 'rate_limit': 0, 'is_load': True},
        {'http_method': 'GET', 'duration': 10000000000, 'initial_wait_time': 0, 'rate_limit': 0, 'is_load': True},
        {'http_method': 'GET', 'duration': 10000000000, 'initial_wait_time': 0, 'rate_limit': 0, 'is_load': True},
        {'http_method': 'GET', 'duration': 10000000000, 'initial_wait_time': 0, 'rate_limit': 0, 'is_load': True},
        {'http_method': 'PUT', 'duration': 2000000000, 'initial_wait_time': 5000000000, 'rate_limit': 10000, 'is_load': False},
        {'http_method': 'PUT', 'duration': 2000000000, 'initial_wait_time': 5000000000, 'rate_limit': 10000, 'is_load': False},
        {'http_method': 'PUT', 'duration': 2000000000, 'initial_wait_time': 5000000000, 'rate_limit': 10000, 'is_load': False},
        {'http_method': 'PUT', 'duration': 2000000000, 'initial_wait_time': 5000000000, 'rate_limit': 10000, 'is_load': False},
    ],
}

download = {
    'testname': 'download_no_load',
    'http_clients': [
        {'http_method': 'GET', 'duration': 2000000000, 'initial_wait_time': 1000000000, 'rate_limit': 10000, 'is_load': False},
        {'http_method': 'GET', 'duration': 2000000000, 'initial_wait_time': 1000000000, 'rate_limit': 10000, 'is_load': False},
        {'http_method': 'GET', 'duration': 2000000000, 'initial_wait_time': 1000000000, 'rate_limit': 10000, 'is_load': False},
        {'http_method': 'GET', 'duration': 2000000000, 'initial_wait_time': 1000000000, 'rate_limit': 10000, 'is_load': False},
    ],
}

download_with_load = {
    'testname': 'download_with_load',
    'http_clients': [
        {'http_method': 'PUT', 'duration': 10000000000, 'initial_wait_time': 0, 'rate_limit': 0, 'is_load': True},
        {'http_method': 'PUT', 'duration': 10000000000, 'initial_wait_time': 0, 'rate_limit': 0, 'is_load': True},
        {'http_method': 'PUT', 'duration': 10000000000, 'initial_wait_time': 0, 'rate_limit': 0, 'is_load': True},
        {'http_method': 'PUT', 'duration': 10000000000, 'initial_wait_time': 0, 'rate_limit': 0, 'is_load': True},
        {'http_method': 'GET', 'duration': 2000000000, 'initial_wait_time': 5000000000, 'rate_limit': 10000, 'is_load': False},
        {'http_method': 'GET', 'duration': 2000000000, 'initial_wait_time': 5000000000, 'rate_limit': 10000, 'is_load': False},
        {'http_method': 'GET', 'duration': 2000000000, 'initial_wait_time': 5000000000, 'rate_limit': 10000, 'is_load': False},
        {'http_method': 'GET', 'duration': 2000000000, 'initial_wait_time': 5000000000, 'rate_limit': 10000, 'is_load': False},
    ],
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
            config_rate_limit = a_client['rate_limit']
            config_initial_wait_time = a_client['initial_wait_time']
            is_load = a_client['is_load']
            http_method = ParseHTTPRequestMethodFromString(config_http_method)
            self.http_client_configs.append({
                'http_method': http_method,
                'duration': config_duration,
                'rate_limit': config_rate_limit,
                'initial_wait_time': config_initial_wait_time,
                'is_load': is_load
            })
        self.testcase = kwargs['testname']

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
            http_client.RequestRateLimitSet(client_config['rate_limit'])
            http_client.RequestStartTypeSet(RequestStartType.Scheduled)
            http_client.RequestInitialTimeToWaitSet(client_config['initial_wait_time'])

            # The client configured duration is in nanoseconds, we want to keep
            # the max_duration as simple as 'seconds', so convert the value.
            client_duration_s = (client_config['initial_wait_time'] + client_config['duration']) / 1e9
            #print("Client Duration:", client_duration_s)
            max_duration = max(max_duration, client_duration_s)
            #print("Max Duration:", max_duration)

            # The RequestStartType is the main configuration difference 
            # Between 2 TCP clients and multiple ones. Rather than starting
            # the client directly, we'll schedule when to start.
            if not client_config['is_load']:
                http_clients.append(http_client)

        print("Server port:", self.server_bb_port.DescriptionGet())
        print("Client port:", self.client_bb_port.DescriptionGet())

        # This is another difference with the basic TCP example.
        # The Start method on a ByteBlower Port starts all scheduled traffic
        # types.  This example this means all configured HTTPClients.
        self.client_bb_port.Start()
        print("Running traffic scenario")

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
            print('%.1fs :: Waiting for clients to finish.' % time_elapsed)

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

        # Process each of the clients.
        results = []
        for client in http_clients:
            results.append(self.process_http_client(client))

        minimum_http_response_time = round(min(results),3)
        average_http_response_time = round(statistics.mean(results),3)

        print("List of HTTP Response Times: ", results)
        print("Minimum HTTP Response Time : {} milliseconds".format(minimum_http_response_time))
        print("Average HTTP Response Time : {} milliseconds".format(average_http_response_time))
        testcase = {}
        testcase['time'] = datetime.datetime.now().__str__()
        testcase['name'] = self.testcase
        testcase['results'] = results
        testcase['minimum'] = minimum_http_response_time
        testcase['average'] = average_http_response_time
        testcases = []
        testcases.append(testcase)
        file = {}
        file['testcases'] = testcases
        with open('data.json', 'w') as json_file:
            # data = json.load(json_file)
            # temp = data['testcases']
            # temp.append(testcase)
            json.dump(file, json_file, indent=4)

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
        initial_wait_time = http_client.RequestInitialTimeToWaitGet()

        print("Local TCP Port     : {} ".format(local_tcp_port))
        print("Direction          : {} ".format(http_method_string))
        print("Requested Duration : {} seconds".format(requested_duration/1e9))
        print("Requested Initial Wait Time : {} seconds".format(initial_wait_time/1e9))

        request_status_value = http_client.RequestStatusGet()

        status = ConvertHTTPRequestStatusToString(request_status_value)
        if not http_client.HasSession():
            print("Status                : {}".format(status))
            print("")

        # The HTTPSession has all the OSI Layer 5 info.
        http_session_info = http_client.HttpSessionInfoGet()
        # Retrieve the latest info from the Server.
        http_session_info.Refresh()
        http_result = http_session_info.ResultGet()
        http_result.Refresh()

        tx_bytes = http_result.TxByteCountTotalGet()
        rx_bytes = http_result.RxByteCountTotalGet()
        avg_throughput = http_result.AverageDataSpeedGet()
        response_time = (http_result.RxTimestampFirstGet() - http_result.TxTimestampFirstGet()) / 1e6

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

        return response_time

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
    #print('Number of arguments:', len(sys.argv), 'arguments.')
    #print('Argument List:', str(sys.argv))
    #print(str(sys.argv[1]))
    if str(sys.argv[1]) == "upload":
        configuration = {**configuration, **upload}
    elif str(sys.argv[1]) == "upload_with_load":
        configuration = {**configuration, **upload_with_load}
    elif str(sys.argv[1]) == "download":
        configuration = {**configuration, **download}
    elif str(sys.argv[1]) == "download_with_load":
        configuration = {**configuration, **download_with_load}
    else:
        configuration = {**configuration, **download_with_load}
    example = Example(**configuration)
    try:
        example.run()
    finally:
        example.cleanup()
