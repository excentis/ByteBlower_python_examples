"""
Basic Ethernet and VLAN frame blasting example for the ByteBlower Python API.
All examples are guaranteed to work with Python 2.7 and above

Copyright 2022, Excentis N.V.
"""

from __future__ import print_function

import math
import sys
from time import sleep

from byteblowerll import byteblower as api

configuration = {
    # Address (IP or FQDN) of the ByteBlower server to use
    'server_address': 'byteblower-tp-1300.lab.byteblower.excentis.com',

    # Configuration for the first ByteBlower port.
    # Will be used as the TX port.
    'port_1_config': {
        'interface': 'trunk-1-19',
        'mac': '00:bb:01:00:00:01',
        # VLAN for this port this can be either an integer or a list of integers.
        # Default: no VLAN
        # examples:
        # A port on VLAN 2
        # 'vlan': 2
        # a port on VLANs 2 and 3, where 2 is the outermost VLAN
        # 'vlan': [ 2, 3 ]
        # a port without VLAN, just ethernet:
        # 'vlan': None
        'vlan': [2, 3]
    },

    # Configuration for the second ByteBlower port.
    # Will be used as RX port.
    'port_2_config': {
        'interface': 'trunk-1-20',
        'mac': '00:bb:01:00:00:02',
        # VLAN for this port this can be either an integer or a list of integers.
        # Default: no VLAN
        # examples:
        # A port on VLAN 2
        # 'vlan': 2
        # a port on VLANs 2 and 3, where 2 is the outermost VLAN
        # 'vlan': [ 2, 3 ]
        # a port without VLAN, just ethernet:
        # 'vlan': None
        'vlan': [2, 3]
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
        byteblower_instance = api.ByteBlower.InstanceGet()
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
        return int(math.ceil(frame_interval))

    @classmethod
    def get_vlans(cls, config):
        vlans = config.get('vlan', [])
        if vlans is None:
            return []

        if isinstance(vlans, int):
            return [vlans]

        return vlans

    def run(self):
        port_1_vlans = self.get_vlans(self.port_1_config)
        ethernet_header_len = 14
        vlan_header_len = 4
        l2_header_without_crc = ethernet_header_len
        l2_header_without_crc += vlan_header_len * len(port_1_vlans)

        byteblower_instance = api.ByteBlower.InstanceGet()

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

        # collect the frame header info.
        # We need to provide the Layer2 (ethernet).
        src_mac = self.port_1.Layer2EthIIGet().MacGet()

        # the destination MAC is the MAC address of the destination port
        dst_mac = self.port_2.Layer2EthIIGet().MacGet()

        payload = 'a' * (self.frame_size - l2_header_without_crc)

        from scapy.layers.l2 import Ether
        from scapy.layers.l2 import Dot1Q
        from scapy.all import Raw
        payload = Raw(payload.encode('ascii', 'strict'))
        eth_header = Ether(src=src_mac, dst=dst_mac)
        scapy_frame = eth_header
        for vlan in port_1_vlans:
            scapy_frame /= Dot1Q(vlan=vlan)

        scapy_frame /= payload

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
        # We will filter on the source and destination mac and also on the
        # VLANs configured at the destination (port2) side.
        bpf_filter = "ether host {src_mac} and ether host {dst_mac}".format(
            src_mac=src_mac, dst_mac=dst_mac)
        port_2_vlans = self.get_vlans(self.port_2_config)
        if len(port_1_vlans):
            bpf_filter += " and vlan {vlan}".format(vlan=port_2_vlans[0])

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
        interface_name = config.get('interface')
        port = self.server.PortCreate(interface_name)  # type: api.ByteBlowerPort
        port_l2 = port.Layer2EthIISet()
        port_l2.MacSet(config['mac'])

        port_vlans = self.get_vlans(config)
        for vlan_id in port_vlans:
            vlan_config = port.Layer25VlanAdd()  # type: api.VLANTag
            vlan_config.IDSet(vlan_id)

        print("Created port", port.DescriptionGet())
        return port


# When this python module is called stand-alone, the run-function must be
# called.  This approach makes it possible to include it in a series of
# examples.
if __name__ == "__main__":
    example = Example(**configuration)
    try:
        example.run()
    except api.ByteBlowerAPIException as e:
        print(e.what(), file=sys.stderr)
        raise
    finally:
        example.cleanup()
