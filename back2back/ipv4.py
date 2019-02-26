"""
Basic IPv4 frameblasting example for the ByteBlower Python API.
All examples are garanteed to work with Python 2.7 and above

Copyright 2018, Excentis N.V.
"""

from __future__ import print_function
from byteblowerll.byteblower import ByteBlower

from time import sleep


configuration = {
    # Address (IP or FQDN) of the ByteBlower server to use
    'server_address': 'byteblower-tp-1300.lab.byteblower.excentis.com',

    # Configuration for the first ByteBlower port.  Will be used as the TX port.
    'port_1_config': {
        'interface': 'trunk-1-13',
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
        'interface': 'trunk-1-14',
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
    'interframegap_nanoseconds': 1000000
}


class Example:
    def __init__(self, **kwargs):
        self.server_address = kwargs['server_address']
        self.port_1_config = kwargs['port_1_config']
        self.port_2_config = kwargs['port_2_config']

        self.number_of_frames = kwargs['number_of_frames']
        self.interframegap_ns = kwargs['interframegap_nanoseconds']

        self.server = None
        self.port_1 = None
        self.port_2 = None

    def run(self):
        byteblower_instance = ByteBlower.InstanceGet()

        print("Connecting to ByteBlower server {}...".format(self.server_address))
        self.server = byteblower_instance.ServerAdd(self.server_address)

        # Create the port which will be the HTTP server (port_1)
        print("Creating TX port")
        self.port_1 = self.provision_port(self.port_1_config)

        print("Creating RX port")
        # Create the port which will be the HTTP client (port_2)
        self.port_2 = self.provision_port(self.port_2_config)

        # now create the stream.  A stream transmits frames on the port on which it is created.
        stream = self.port_1.TxStreamAdd()

        # set the number of frames to transmit
        stream.NumberOfFramesSet(self.number_of_frames)

        # set the speed of the transmission
        stream.InterFrameGapSet(self.interframegap_ns)

        # a stream transmits frames, so we need to tell the stream which frames we want to transmit
        frame = stream.FrameAdd()

        # collect the frame header info.  We need to provide the Layer2 (ethernet) and Layer3 (IPv4) addresses.
        src_ip = self.port_1_config['ip_address']
        src_mac = self.port_1.Layer2EthIIGet().MacGet()

        dst_ip = self.port_2_config['ip_address']

        # the destination MAC is the MAC address of the destination port if the destination port is in the same
        # subnet as the source port, otherwise it will be the MAC address of the gateway.
        # ByteBlower has a function to resolve the correct MAC address in the Layer3 configuration object
        dst_mac = self.port_1.Layer3IPv4Get().Resolve(dst_ip)

        frame_size = 512
        udp_src = 4096
        udp_dest = 4096
        payload = 'a' * (frame_size - 42)

        from scapy.layers.inet import UDP, IP, Ether, Raw
        scapy_udp_payload = Raw(payload.encode('ascii', 'strict'))
        scapy_udp_header = UDP(dport=udp_dest, sport=udp_src)
        scapy_ip_header = IP(src=src_ip, dst=dst_ip)
        scapy_frame = Ether(src=src_mac, dst=dst_mac) / scapy_ip_header / scapy_udp_header / scapy_udp_payload

        frame_content = bytearray(bytes(scapy_frame))

        # The ByteBlower API expects an 'str' as input for the Frame::BytesSet(), we need to convert the bytearray
        hexbytes = ''.join((format(b, "02x") for b in frame_content))

        frame.BytesSet(hexbytes)

        # create a trigger.  A trigger is an object which receives data.
        # The Basic trigger just count packets
        trigger = self.port_2.RxTriggerBasicAdd()

        # every trigger needs to know on which frames it will work.  The default filter is no filter, so it will
        # analyze every frame, which is not what we want here.
        # We will filter on the destination IP and the destination UDP port
        bpf_filter = "ip dst {} and udp port {}".format(dst_ip, udp_dest)
        trigger.FilterSet(bpf_filter)

        # print the configuration, this makes it easy to review what we have done until now
        print("Current ByteBlower configuration:")
        print("port1:", self.port_1.DescriptionGet())
        print("port2:", self.port_2.DescriptionGet())

        # start the traffic, clear the latency trigger.  Triggers are active as soon they are created, so
        # we may want to clear the data it already has collected.
        print("Starting traffic")
        trigger.ResultClear()
        stream_history = stream.ResultHistoryGet()
        trigger_history = trigger.ResultHistoryGet()

        duration_ns = self.interframegap_ns * self.number_of_frames
        duration_s = duration_ns / 1000000000 + 1

        stream.Start()

        # duration_s is a float, so we need to cast it to an integer first
        for iteration in range(1, int(duration_s)):
            # sleep one second
            sleep(1)

            # Refresh the history, the ByteBlower server will create interval and cumulative results every
            # second (by default).  The Refresh method will synchronize the server data with the client.
            stream_history.Refresh()
            trigger_history.Refresh()

            last_interval_tx = stream_history.IntervalLatestGet()
            last_interval_rx = trigger_history.IntervalLatestGet()

            print("Sent {TX} frames, received {RX} frames".format(
                TX=last_interval_tx.PacketCountGet(),
                RX=last_interval_rx.PacketCountGet()
            ))

        print("Done sending traffic (time elapsed)")

        # Waiting for a second after the stream is finished.
        # This has the advantage that frames that were transmitted but not received yet,
        # can be processed by the server
        print("Waiting for a second")
        sleep(1)

        # During the test itself we queried the interval counters, there are also cumulative counters.
        # The last cumulative counter available in the history is also available as the Result
        stream_result = stream.ResultGet()
        oos_result = trigger.ResultGet()
        stream_result.Refresh()
        print("Stream result:", stream_result.DescriptionGet())
        oos_result.Refresh()
        print("Out of sequence result:", oos_result.DescriptionGet())

        tx_frames = stream_result.PacketCountGet()
        rx_frames = oos_result.PacketCountGet()

        print("Sent {TX} frames, received {RX} frames".format(TX=tx_frames, RX=rx_frames))

        # It is considered good practice to clean up your objects.  This tells the ByteBlower server it can
        # clean up its resources.
        self.server.PortDestroy(self.port_1)
        self.server.PortDestroy(self.port_2)

        # Disconnect from the ByteBlower server
        byteblower_instance.ServerRemove(self.server)

        return [tx_frames, rx_frames]

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
