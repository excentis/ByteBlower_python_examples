"""
    This example script demonstrates a ping flood.It can be used
    to test resistance to ping-flood or rate limiting by the device.

    The script uses 4 input parameters
      - The address of the ByteBlower Server
      - The byteblower interface to launch the attoc from
      - The ByteBlower target interface, where are you sending the traffic to.
      - The speed to send out the traffic, expressed in Mbit/s. The parameter is optional, default
          speed is 1000 Mbit/s

    It's a demonstration script. To keep things simple, the ByteBlower
    interfaces are configured using DHCP. 
"""
from __future__ import print_function
import sys
import random
from time import sleep

from byteblowerll.byteblower import ByteBlower

from scapy.all import Raw, Ether, IP, ICMP


def create_mac_address():
    byte_val = ['00', 'bb'
                ] + ['%02x' % random.randint(0, 255) for _ in range(6)]
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
    frameContent = bytearray(bytes(sc_frame))
    hexbytes = ''.join((format(b, "02x") for b in frameContent))
    frame_size = len(hexbytes) / 2
    frame_overhead = 24

    frame = stream.FrameAdd()
    frame.BytesSet(hexbytes)

    gap = (frame_size + frame_overhead) / float(speed)
    stream.InterFrameGapSet(int(1e9 * gap))
    duration = 10
    n_frames = int(duration / gap)
    stream.NumberOfFramesSet(n_frames)

    stream.Start()
    print("Waiting for %.2f sec" % (duration))
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

    return (n_frames, 1 / gap, rx_echo, rx_reply)


if "__main__" == __name__:

    server_address = sys.argv[
        1]  #'byteblower-tp-3100.lab.byteblower.excentis.com'
    byteblower_instance = ByteBlower.InstanceGet()
    server = byteblower_instance.ServerAdd(server_address)

    src = create_port(server, sys.argv[2])  #'trunk-1-49')
    dst = create_port(server, sys.argv[3])  #'trunk-1-50')
    a_mbit = 1e6

    speed = 999
    if len(sys.argv) == 5:
        speed = float(sys.argv[4])

    n_req, fps, rx_echo, rx_replies = test_connection(src, dst, speed * a_mbit)
    summary_txt = """
    Send out %d Ping requests at %d Mbit/s (%.2f requests a second)
    %d (%.1f %% ) were received at the destination.
    %d (%.1f %% ) were answered at the source.
    """ % (n_req, speed, fps, rx_echo, (100. * rx_echo) / n_req, rx_replies,
           (100. * rx_replies) / n_req)
    print(summary_txt)
