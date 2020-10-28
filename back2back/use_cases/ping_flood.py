"""
    This example script demonstrates a ping flood. It can be used to test the
    resistance to a ping-flood or rate limiting by the device.

    The script uses 4 input parameters
      - The address of the ByteBlower Server
      - The byteblower interface to launch the attack from
      - The ByteBlower target interface, where are you sending the traffic to.
      - The speed to send out the traffic, expressed in Mbit/s.
        The parameter is optional, default speed is 1000 Mbit/s

    An example input and associated output are shown in the lines below.

    $ python ping_flood.py byteblower.lab.excentis.com trunk-1-86 nontrunk-1 10

    > Waiting for 10.00 sec
    >
    > Send out 67204 Ping requests at 10 Mbit/s (6720.43 requests a second)
    > 19042 (28.3 % ) were received at the destination.
    > 7737 (11.5 % ) were answered at the source.

    It's a demonstration script. To keep things simple,
    the ByteBlower interfaces are configured using DHCP.
"""
from __future__ import print_function

import random
import sys
import time

from byteblowerll.byteblower import ByteBlower
from scapy.all import Raw, Ether, IP, ICMP


def create_mac_address():
    byte_val = ['00', 'bb'] + \
               ['%02x' % random.randint(0, 255) for _ in range(6)]
    return ':'.join(byte_val)


def create_port(server, bb_interface_name):
    port = server.PortCreate(bb_interface_name)
    l2 = port.Layer2EthIISet()
    l2.MacSet(create_mac_address())

    l3 = port.Layer3IPv4Set()
    l3.ProtocolDhcpGet().Perform()

    return port


def test_connection(src, dst, speed):
    src_addr = src.Layer3IPv4Get().IpGet()
    dst_addr = dst.Layer3IPv4Get().IpGet()
    src_mac = src.Layer2EthIIGet().MacGet()
    dst_mac = src.Layer3IPv4Get().Resolve(dst_addr)

    echo_trigger = dst.RxTriggerBasicAdd()
    echo_trigger.FilterSet("icmp[icmptype] == icmp-echo")

    reply_trigger = src.RxTriggerBasicAdd()
    reply_trigger.FilterSet("icmp[icmptype] == icmp-echoreply")

    stream = src.TxStreamAdd()
    sc_frame = Ether(
        src=src_mac, dst=dst_mac) / IP(
        src=src_addr, dst=dst_addr) / ICMP() / Raw("AA" * 60)

    frame_content = bytearray(bytes(sc_frame))
    hexbytes = ''.join((format(b, "02x") for b in frame_content))
    frame_size = len(hexbytes) / 2
    frame_overhead = 24

    frame = stream.FrameAdd()
    frame.BytesSet(hexbytes)

    gap = ((frame_size + frame_overhead) * 8.) / speed
    stream.InterFrameGapSet(int(1e9 * gap))
    duration = 10
    n_frames = int(duration / gap)
    stream.NumberOfFramesSet(n_frames)

    stream.Start()
    print("Waiting for %.2f sec" % duration)
    time.sleep(duration)
    time.sleep(0.2)

    stream.Stop()

    echo_trigger.ResultGet().Refresh()
    reply_trigger.ResultGet().Refresh()

    rx_echo = echo_trigger.ResultGet().PacketCountGet()
    rx_reply = reply_trigger.ResultGet().PacketCountGet()

    dst.RxTriggerBasicRemove(echo_trigger)
    src.RxTriggerBasicRemove(reply_trigger)
    src.TxStreamRemove(stream)

    return n_frames, 1 / gap, rx_echo, rx_reply


def main(server_address, src_interface, dst_interface, speed_mbps=999):
    byteblower_instance = ByteBlower.InstanceGet()
    server = None
    try:
        server = byteblower_instance.ServerAdd(server_address)

        src = create_port(server, src_interface)
        dst = create_port(server, dst_interface)
        a_mbit = 1e6

        n_req, fps, rx_echo, rx_replies = test_connection(src, dst, speed_mbps * a_mbit)
        summary_txt = """
            Send out %d Ping requests at %d Mbit/s (%.2f requests a second)
            %d (%.1f %% ) were received at the destination.
            %d (%.1f %% ) were answered at the source.
            """ % (n_req, speed_mbps, fps, rx_echo, (100. * rx_echo) / n_req, rx_replies,
                   (100. * rx_replies) / n_req)
        print(summary_txt)
    finally:
        if server is not None:
            byteblower_instance.ServerRemove(server)


if "__main__" == __name__:
    if not 4 <= len(sys.argv) <= 5:
        print(__doc__)
        print("Wrong number of arguments")
        sys.exit(-1)

    main(server_address=sys.argv[1], src_interface=sys.argv[2],
         dst_interface=sys.argv[3],
         speed_mbps=float(sys.argv[4]) if len(sys.argv) == 5 else 999)
