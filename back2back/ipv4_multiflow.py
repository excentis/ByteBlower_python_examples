"""
Basic IPv4 frame blasting example with multiple flows for the ByteBlower
Python API.  This example demonstrates the use of PortsStart and ResultsRefresh
to multiple ByteBlower ports at once and fetch multiple results at once.
All examples are guaranteed to work with Python 2.7 and above

Copyright 2020, Excentis N.V.
"""

from __future__ import print_function

from time import sleep

from byteblowerll.byteblower import ByteBlower
from byteblowerll.byteblower import AbstractRefreshableResultList
from byteblowerll.byteblower import ByteBlowerPortList

configuration = {
    # Address (IP or FQDN) of the ByteBlower server to use
    'server_address': 'byteblower-tp-1300.lab.byteblower.excentis.com',

    # Configuration for the first ByteBlower port.  Will be used as the TX port.
    'port_1_config': {
        'interface': 'nontrunk-1',
        'mac': '00:bb:01:00:00:01',
        # IP configuration for the ByteBlower Port.  Only IPv4 is supported
        # Options are 'DHCPv4', 'static'
        # if DHCPv4, use "dhcpv4"
        'ip': 'dhcpv4',
        # if staticv4, use ["ipaddress", netmask, gateway]
        # 'ip': ['192.168.0.2', "255.255.255.0", "192.168.0.1"],
    },

    # Configuration for the second ByteBlower port.  Will be used as RX port.
    'port_2_config': {
        'interface': 'trunk-1-13',
        'mac': '00:bb:01:00:00:02',
        # IP configuration for the ByteBlower Port.  Only IPv4 is supported
        # Options are 'DHCPv4', 'static'
        # if DHCPv4, use "dhcpv4"
        'ip': 'dhcpv4',
        # if staticv4, use ["ipaddress", netmask, gateway]
        # 'ip': ['192.168.0.2', "255.255.255.0", "192.168.0.1"],
    },

    # number of frames to send.
    'number_of_frames': 10000,

    # Inter frame gap to use in nanoseconds.
    # example: 1000000ns is 1ms, which is 1000pps
    'interframegap_nanoseconds': 1000000,

    # Number of flows to send in each direction:
    # - Downstream: traffic from port_1 to port_2
    # - Upstream: traffic from port_2 to port_1
    'number_of_downstream_flows': 3,
    'number_of_upstream_flows': 2
}


class Example:
    def __init__(self, **kwargs):
        self.server_address = kwargs['server_address']
        self.port_1_config = kwargs['port_1_config']
        self.port_2_config = kwargs['port_2_config']

        self.number_of_frames = kwargs['number_of_frames']
        self.interframegap_ns = kwargs['interframegap_nanoseconds']

        self.number_of_downstream_flows = kwargs['number_of_downstream_flows']
        self.number_of_upstream_flows = kwargs['number_of_upstream_flows']

        self.server = None
        self.port_1 = None
        self.port_2 = None

        self.udp_src = 4096
        self.udp_dst = 4096

    def run(self):
        byteblower_instance = ByteBlower.InstanceGet()

        print("Connecting to ByteBlower server %s..." % self.server_address)
        self.server = byteblower_instance.ServerAdd(self.server_address)

        # Create the port which will be the HTTP server (port_1)
        print("Creating port 1")
        self.port_1 = self.provision_port(self.port_1_config)

        print("Creating port 2")
        # Create the port which will be the HTTP client (port_2)
        self.port_2 = self.provision_port(self.port_2_config)

        results_to_refresh = AbstractRefreshableResultList()
        flows = []

        transmitting_ports = set()
        for (src_port, dst_port, number_of_flows) in [
            # Downstream flows flow from port_1 to port_2
            (self.port_1, self.port_2, self.number_of_downstream_flows),
            # Upstream flows flow from port_2 to port_1
            (self.port_2, self.port_1, self.number_of_upstream_flows)
        ]:
            for i in range(number_of_flows):
                print("Creating flow {i} from {src_ip} to {dst_ip}".format(
                    i=i + 1,
                    src_ip=src_port.Layer3IPv4Get().IpGet(),
                    dst_ip=dst_port.Layer3IPv4Get().IpGet()
                ))
                stream, trigger = self.create_flow(src_port=src_port,
                                                   dst_port=dst_port)
                flows.append((src_port, dst_port, stream, trigger))

                transmitting_ports.add(src_port)

                # Add the results we are interested in into a list of results
                # we want to refresh
                results_to_refresh.append(stream.ResultGet())
                results_to_refresh.append(stream.ResultHistoryGet())
                results_to_refresh.append(trigger.ResultGet())
                results_to_refresh.append(trigger.ResultHistoryGet())

        # print the configuration, this makes it easy to review what we have
        # done until now
        print("Current ByteBlower configuration:")
        print("port1:", self.port_1.DescriptionGet())
        print("port2:", self.port_2.DescriptionGet())

        # start the traffic, clear the trigger.  Triggers are active as soon
        # they are created, so  we may want to clear the data it already has
        # collected.

        print("Clearing triggers")
        for tx_port, rx_port, stream, trigger in flows:
            trigger.ResultClear()

        print("Starting traffic")
        ports_to_start = ByteBlowerPortList()
        for tx_port in transmitting_ports:
            ports_to_start.push_back(tx_port)
        # Start all ports at the same time.
        self.server.PortsStart(ports_to_start)

        duration_ns = self.interframegap_ns * self.number_of_frames
        duration_s = duration_ns / 1000000000 + 1

        # Let's loop over the next code for the duration and an additional
        # second.  We are waiting an extra second so when frames are sent on
        # the edge of an interval boundary, it *can* arrive in the next
        # result interval.  We want to be sure it is received and counted.
        # In the ideal case, the last result printed, will contain 0 frames
        # sent and 0 frames received
        for iteration in range(0, int(duration_s) + 1):
            # sleep one second
            sleep(1)

            print("Refreshing results after %d seconds..." % (iteration + 1))
            # Refresh all results at the same time
            # This synchronises the results on the server with the results
            # available in the ByteBlower API.  These results are the current
            # results and the history over time.  Refreshing them at the same
            # time using ResultsRefresh has a few advantages since this is done
            # in a *single* API call, thus eliminating extra round-trips
            # between the API and the ByteBlower Server.
            # These roundtrips can be significant when comparing results from
            # e.g. a Stream and a Trigger.
            byteblower_instance.ResultsRefresh(results_to_refresh)

            for i, (src_port, dst_port, stream, trigger) in enumerate(flows):
                tx_interval = stream.ResultHistoryGet().IntervalLatestGet()
                rx_interval = trigger.ResultHistoryGet().IntervalLatestGet()

                print("  Flow %d from %s to %s sent %d frames, "
                      "received %d frames" % (i + 1,
                                              src_port.Layer3IPv4Get().IpGet(),
                                              dst_port.Layer3IPv4Get().IpGet(),
                                              tx_interval.PacketCountGet(),
                                              rx_interval.PacketCountGet())
                      )

        print("Done sending traffic (time elapsed)")

        # During the test itself we queried the interval counters, there are
        # also cumulative counters.  The last cumulative counter available in
        # the history is also available as the Result
        result = []
        for i, (src_port, dst_port, stream, trigger) in enumerate(flows):
            tx_result = stream.ResultGet()
            rx_result = trigger.ResultGet()

            tx_frames = tx_result.PacketCountGet()
            rx_frames = rx_result.PacketCountGet()
            print("Flow %d from %s to %s sent %d frames, "
                  "received %d frames" % (i + 1,
                                          src_port.Layer3IPv4Get().IpGet(),
                                          dst_port.Layer3IPv4Get().IpGet(),
                                          tx_frames, rx_frames)
                  )
            result.append((tx_frames, rx_frames))

        return result

    def cleanup(self):
        """Cleanup the created ByteBlower objects

        It is considered good practice to clean up your objects.  This tells
        the ByteBlower server it can clean up its resources.
        """
        if self.port_1:
            self.server.PortDestroy(self.port_1)
            self.port_1 = None
        if self.port_2:
            self.server.PortDestroy(self.port_2)

        # Disconnect from the ByteBlower server
        if self.server:
            ByteBlower.InstanceGet().ServerRemove(self.server)
            self.server = None

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

    def create_flow(self, src_port, dst_port):
        """Create a ByteBlower stream and matching Trigger

        Returns a tuple of byteblowerll.byteblower.TxStream and
        a byteblowerll.byteblower.RxTriggerBasic

        :param src_port: Port to create the transmitting side of the flow on
        :type src_port: byteblowerll.byteblower.ByteBlowerPort
        :param dst_port: Port to create the receiving side of the flow on.
        :type dst_port: byteblowerll.byteblower.ByteBlowerPort

        :rtype: tuple
        """

        src_port_l3 = src_port.Layer3IPv4Get()
        dst_port_l3 = dst_port.Layer3IPv4Get()

        # Create the stream
        stream = src_port.TxStreamAdd()

        # set the number of frames to transmit
        stream.NumberOfFramesSet(self.number_of_frames)

        # set the speed of the transmission
        stream.InterFrameGapSet(self.interframegap_ns)

        # a stream transmits frames, so we need to tell the stream which frames
        # we want to transmit
        frame = stream.FrameAdd()

        # collect the frame header info.  We need to provide the
        # Layer2 (ethernet) and Layer3 (IPv4) addresses.
        src_ip = src_port_l3.IpGet()
        src_mac = src_port.Layer2EthIIGet().MacGet()

        dst_ip = dst_port_l3.IpGet()

        # the destination MAC is the MAC address of the destination port if the
        # destination port is in the same subnet as the source port, otherwise
        # it will be the MAC address of the gateway.  ByteBlower has a function
        # to resolve the correct MAC address in the Layer3 configuration
        # object.
        dst_mac = src_port_l3.Resolve(dst_ip)

        frame_size = 512

        payload = 'a' * (frame_size - 42)

        from scapy.layers.inet import UDP, IP, Ether
        from scapy.all import Raw
        udp_payload = Raw(payload.encode('ascii', 'strict'))
        udp_header = UDP(dport=self.udp_dst, sport=self.udp_src)
        ip_header = IP(src=src_ip, dst=dst_ip)
        eth_header = Ether(src=src_mac, dst=dst_mac)
        scapy_frame = eth_header / ip_header / udp_header / udp_payload

        frame_content = bytearray(bytes(scapy_frame))

        # The ByteBlower API expects an 'str' as input for the
        # Frame::BytesSet(), we need to convert the bytearray
        hexbytes = ''.join((format(b, "02x") for b in frame_content))

        frame.BytesSet(hexbytes)

        # create a trigger.  A trigger is an object which receives data.
        # The Basic trigger just count packets
        trigger = dst_port.RxTriggerBasicAdd()

        # every trigger needs to know on which frames it will work.  The
        # default filter is no filter, so it will analyze every frame, which
        # is not what we want here.  We will filter on the destination IP and
        # the destination UDP port
        bpf_filter = "ip dst {} and udp port {}".format(dst_ip, self.udp_dst)
        trigger.FilterSet(bpf_filter)

        # increment src and destination UDP ports so we have unique pot numbers
        # with every flow
        self.udp_src += 1
        self.udp_dst += 1

        return stream, trigger


# When this python module is called stand-alone, the run-function must be
# called.  This approach makes it possible to include it in a series of
# examples.
if __name__ == "__main__":
    example = Example(**configuration)
    try:
        example.run()
    finally:
        example.cleanup()
