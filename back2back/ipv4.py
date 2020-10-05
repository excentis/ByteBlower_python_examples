"""
Basic IPv4 frame blasting example for the ByteBlower Python API.
All examples are guaranteed to work with Python 2.7 and above

Copyright 2018, Excentis N.V.
"""

from __future__ import print_function

import math
from time import sleep

from byteblowerll.byteblower import ByteBlower

configuration = {
    # Address (IP or FQDN) of the ByteBlower server to use
    'server_address': 'byteblower-tp-1300.lab.byteblower.excentis.com',

    # Configuration for the first ByteBlower port.
    # Will be used as the TX port.
    'port_1_config': {
        'interface': 'trunk-1-13',
        'mac': '00:bb:01:00:00:01',
        # IP configuration for the ByteBlower Port.  Only IPv4 is supported
        # Options are 'DHCPv4', 'static'
        # if DHCPv4, use "dhcpv4"
        # 'ip': 'dhcpv4',
        # if staticv4, use ["ipaddress", netmask, gateway]
        'ip': ['192.168.0.2', "255.255.255.0", "192.168.0.1"],
    },

    # Configuration for the second ByteBlower port.
    # Will be used as RX port.
    'port_2_config': {
        'interface': 'trunk-1-14',
        'mac': '00:bb:01:00:00:02',
        # IP configuration for the ByteBlower Port.  Only IPv4 is supported
        # Options are 'DHCPv4', 'static'
        # if DHCPv4, use "dhcpv4"
        # 'ip': 'dhcpv4',
        # if staticv4, use ["ipaddress", netmask, gateway]
        'ip': ['192.168.0.2', "255.255.255.0", "192.168.0.1"],
    },

    # number of frames to send.
    'number_of_frames': 10000,

    # Size of the frames to be sent (without CRC).
    # Unit: Bytes
    'frame_size': 512,

    # Inter frame gap to use in nanoseconds.
    # Using the throughput configuration variable above, a throughput value can
    # be passed to the example script.  The inter frame gap will then be
    # calculated using that value.
    # example: 1000000ns is 1ms, which is 1000pps
    'interframegap_nanoseconds': 1000000,

    # Instead of configuring the inter-frame gap above, one can specify a
    # desired throughput too.  This conversion will be done in the __init__
    # function of the example.
    # When set, the throughput is used, otherwise interframegap above will
    # be used.
    # Units: Mbit/s
    # 'throughput': 400
}


class Example:
    def __init__(self, **kwargs):
        self.server_address = kwargs['server_address']
        self.port_1_config = kwargs['port_1_config']
        self.port_2_config = kwargs['port_2_config']

        self.number_of_frames = kwargs['number_of_frames']
        self.frame_size = kwargs['frame_size']

        self.interframegap_ns = kwargs['interframegap_nanoseconds']

        throughput = kwargs.pop('throughput', None)
        if throughput is not None:
            self.interframegap_ns = self.calculate_interframegap(throughput)
            print("%d Mbit/s translates to an inter-frame-gap of %d ns" %
                  (throughput, self.interframegap_ns))

        self.server = None
        self.port_1 = None
        self.port_2 = None

    def cleanup(self):
        """Clean up the created objects"""
        byteblower_instance = ByteBlower.InstanceGet()
        if self.port_1:
            self.server.PortDestroy(self.port_1)
            self.port_1 = None

        if self.port_2:
            self.server.PortDestroy(self.port_2)
            self.port_2 = None

        if self.server is not None:
            byteblower_instance.ServerRemove(self.server)
            self.server = None

    def calculate_interframegap(self, throughput):
        """Calculate the frame interval for a specific throughput

        The frame interval (called interframegap in the API) is the time
        between the start of 2 subsequent frames.   For any given throughput
        and frame size this can be calculated as following:

          frame interval = total frame size / throughput

        where the throughput is in bits per second and the frame size in bits.

        Since the given frame size is Layer2 without CRC, the conversion to
        Layer1 size needs to be done:
            l1 = pause + preamble + start of frame delimiter + l2

        The pause is 12 bytes, the preamble and sfd are 8 bytes.  The
        configured frame size is l2 without CRC, so 4 bytes CRC need to
        be added.

        :param throughput: The throughput in Mbits/s
        :type throughput: float

        :return: The ifg rounded up for use in the API in nanoseconds
        :rtype: int
        """
        crc_len = 4
        pause = 12
        preamble_sfd = 8

        # An ethernet frame consists of a pause, a preamble, the frame itself
        # since the frame size is configured without CRC, it needs to be added
        total_frame_size = pause + preamble_sfd + self.frame_size + crc_len

        frame_size_bits = total_frame_size * 8

        # Throughput is in Mbits/s, so we need to get the value in bits/s
        frames_per_second = throughput * 1e6 / frame_size_bits

        # The inter-frame-gap is the interval between the beginning of 2 frames
        # in nanoseconds, so we have to divide one second worth of nanoseconds
        # through the number of frames per second to get it.
        frame_interval = 1e9 / frames_per_second

        # return the closest integer, since the API only allows integers to be
        # passed
        return math.ceil(frame_interval)

    def run(self):
        udp_src = 4096
        udp_dest = 4096

        byteblower_instance = ByteBlower.InstanceGet()

        print("Connecting to ByteBlower server %s..." % self.server_address)
        self.server = byteblower_instance.ServerAdd(self.server_address)

        # Create the port which will be the HTTP server (port_1)
        print("Creating TX port")
        self.port_1 = self.provision_port(self.port_1_config)

        print("Creating RX port")
        # Create the port which will be the HTTP client (port_2)
        self.port_2 = self.provision_port(self.port_2_config)

        # now create the stream.
        # A stream transmits frames on the port on which it is created.
        stream = self.port_1.TxStreamAdd()

        # set the number of frames to transmit
        stream.NumberOfFramesSet(self.number_of_frames)

        # set the speed of the transmission
        stream.InterFrameGapSet(self.interframegap_ns)

        # Since a stream transmits frames, we need to tell the stream which
        # frames we want to transmit
        frame = stream.FrameAdd()

        # collect the frame header info.  We need to provide the Layer2
        # (ethernet) and Layer3 (IPv4) addresses.
        src_ip = self.port_1_config['ip_address']
        src_mac = self.port_1.Layer2EthIIGet().MacGet()

        dst_ip = self.port_2_config['ip_address']

        # the destination MAC is the MAC address of the destination port if
        # the destination port is in the same subnet as the source port,
        # otherwise it will be the MAC address of the gateway.
        # ByteBlower has a function to resolve the correct MAC address in
        # the Layer3 configuration object
        dst_mac = self.port_1.Layer3IPv4Get().Resolve(dst_ip)

        payload = 'a' * (self.frame_size - 42)

        from scapy.layers.inet import UDP, IP, Ether
        from scapy.all import Raw
        udp_payload = Raw(payload.encode('ascii', 'strict'))
        udp_header = UDP(dport=udp_dest, sport=udp_src)
        ip_header = IP(src=src_ip, dst=dst_ip)
        eth_header = Ether(src=src_mac, dst=dst_mac)
        scapy_frame = eth_header / ip_header / udp_header / udp_payload

        frame_content = bytearray(bytes(scapy_frame))

        # The ByteBlower API expects an 'str' as input for the
        # frame::BytesSet() method, we need to convert the bytearray
        hexbytes = ''.join((format(b, "02x") for b in frame_content))

        frame.BytesSet(hexbytes)

        # create a trigger.  A trigger is an object which receives data.
        # The Basic trigger just count packets
        trigger = self.port_2.RxTriggerBasicAdd()

        # every trigger needs to know on which frames it will work.
        # The default filter is no filter, so it will analyze every frame,
        # which is not what we want here.
        # We will filter on the destination IP and the destination UDP port
        bpf_filter = "ip dst {} and udp port {}".format(dst_ip, udp_dest)
        trigger.FilterSet(bpf_filter)

        # print the configuration.
        # his makes it easy to review what we have done until now
        print("Current ByteBlower configuration:")
        print("port1:", self.port_1.DescriptionGet())
        print("port2:", self.port_2.DescriptionGet())

        # start the traffic and clear the trigger.
        # Triggers are active as soon they are created, so we may want to clear
        # the data it already has collected.
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

            # Refresh the history, the ByteBlower server will create interval
            # and cumulative results every second (by default).  The Refresh()
            # method will synchronize the server data with the client.
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
        # This has the advantage that frames that were transmitted
        # but not received yet, can be processed by the server
        print("Waiting for a second")
        sleep(1)

        # During the test itself we queried the interval counters,
        # there are also cumulative counters.  The last cumulative counter
        # available in the history is also available as the Result
        stream_result = stream.ResultGet()
        stream_result.Refresh()
        print("Stream result:", stream_result.DescriptionGet())

        trigger_result = trigger.ResultGet()
        trigger_result.Refresh()
        print("Trigger result:", trigger_result.DescriptionGet())

        tx_frames = stream_result.PacketCountGet()
        rx_frames = trigger_result.PacketCountGet()

        print("Sent {TX} frames, received {RX} frames".format(TX=tx_frames, RX=rx_frames))

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
    example = Example(**configuration)
    try:
        example.run()
    finally:
        example.cleanup()
