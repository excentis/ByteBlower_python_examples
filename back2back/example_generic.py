# Needed for python2 / python3 print function compatibility
from __future__ import print_function
# Import scapy, needed for creation of UDP frames
import scapy


def create_port(server, interface, mac_address, ip_mode="ipv4", use_dhcp=True, ip_address=None, netmask=None, gateway=None):
    print("Creating a ByteBlower Port on interface {}".format(interface))
    port = server.PortCreate(interface)
    
    print("  - Setting MAC address: {}".format(mac_address))
    l2 = port.Layer2EthIISet()
    l2.AddressSet(mac_address)
    
    print("  - Configuring Layer3 ({})".format(ip_mode))
    l3 = None
    if ip_mode == "ipv4":
        l3 = port.Layer3IPv4Set()
    else:
        l3 = port.Layer3IPv6Set()

    if use_dhcp:
        l3.ProtocolDhcpGet().Perform()
    else:
        if ip_mode == "ipv4":
            l3.IpSet(ip_address)
            l3.NetmaskSet(netmask)
            l3.GatewaySet(gateway)
        else:
            l3.IPManualSet(ip_address)

    return port


def create_flow_ipv4_udp(srcPort, dstPort, ethernetLength, srcUdpPort, dstUdpPort, numberOfFrames, interframeGap):
    """
        Creates a "flow", which is a combination of a
          - stream from a source port to a destinationport
          - trigger on the destination port which counts the incoming packets
    """
    srcMac = srcPort.Layer2EthIIGet().AddressGet()
    srcIp = srcPort.Layer3IPv4Get().IpGet()
    dstIp = dstPort.Layer3IPv4Get().IpGet()
    dstMac = srcPort.Layer3IPv4Get().Resolve(dstIp)
    frame = create_frame_ipv4_udp(dstMac, srcMac, dstIp, srcIp, dstUdpPort, srcUdpPort, ethernetLength)
    stream = create_stream(srcPort, frame, numberOfFrames, interframeGap)
    trigger = create_trigger(srcPort, dstPort, srcUdpPort, dstUdpPort)
    
    return stream, trigger


def create_stream(srcPort, frame_bytes, numberOfFrames, interframeGap):
    """
        Creates a stream using the given
          - source port,
          - frame bytes,
          - number of frames
          - inter frame gap

        Known limitations:
          - frame_bytes must be of "<byte1><byte2>..." e.g. "00ff1f..."
          - interframeGap must be in nanoseconds
    """
    stream = srcPort.TxStreamAdd()
    frame = stream.FrameAdd()
    frame.BytesSet(frame_bytes)
    stream.NumberOfFramesSet(numberOfFrames)
    stream.InterFrameGapSet(interframeGap)
    return stream


def create_trigger(srcPort, dstPort, srcUdpPort, dstUdpPort):
    trigger = dstPort.RxTriggerBasicAdd()

    trigger.FilterSet("ip src {} and ip dst {} and udp and src port {} and dst port {}".format(srcPort.Layer3IPv4Get().IpGet(), dstPort.Layer3IPv4Get().IpGet(), srcUdpPort, dstUdpPort))
    
    return trigger


def create_frame_ipv4_udp(dstMac, srcMac, dstIp, srcIp, dstUdpPort, srcUdpPort, length):
    data = 'a' * (length - 42)
    from scapy.layers.inet import UDP,IP, Ether, Raw

    # Works fine in Python3 and Python2
    # 1. Scapy expects 'bytes' input
    # 2. There are string (encoding and functionality) incompatibilities in Python2 vs. Python3
    #    (cfr. build-in types 'str' and 'bytes')
    #    data.encode('ascii', 'strict') runs our data into correct (read: supported) 'bytes' format
    frame = Ether(src=srcMac, dst=dstMac) / IP(src=srcIp, dst=dstIp) / UDP(dport=dstUdpPort, sport=srcUdpPort) / Raw(data.encode('ascii', 'strict'))

    # Works in Python3 and Python2:
    # 1. There are string (encoding and functionality) incompatibilities in Python2 vs. Python3
    #    (cfr. build-in types 'str' and 'bytes')
    #    The only built-in type which is backward compatible is the 'bytearray'
    # 2. scapy frame has support for conversion to 'bytes', but not immediately to 'bytearray'
    # See also https://docs.python.org/release/3.0.1/whatsnew/3.0.html#text-vs-data-instead-of-unicode-vs-8-bit
    frameContent = bytearray(bytes(frame))

    # The ByteBlower API expects an 'str' as input for the Frame::BytesSet(),
    # Therefore we convert is right here.
    # hexbytes = ""
    # for some_byte in frameContent:
    #     hexbytes = hexbytes + format(some_byte, "02x")
    # Shortcut using generator
    hexbytes = ''.join((format(b, "02x") for b in frameContent))

    return hexbytes
