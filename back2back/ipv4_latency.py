"""
Basic IPv4 with latency measurement example for the ByteBlower Python API.
All examples are garanteed to work with Python 2.7 and above

Copyright 2018, Excentis N.V.
"""

from __future__ import print_function
from byteblowerll.byteblower import ByteBlower, DHCPFailed
from example_generic import create_frame_ipv4_udp

from time import sleep


def initialize_port(server, interface, mac_address):
    # Create the port on the interface
    port = server.PortCreate(interface)

    # a host has a MAC address and an IP address, so initialize those
    eth_configuration = port.Layer2EthIISet()
    eth_configuration.MacSet(mac_address)

    ipv4_configuration = port.Layer3IPv4Set()
    # lets do DHCP
    dhcp_protocol = ipv4_configuration.ProtocolDhcpGet()
    try:
        dhcp_protocol.Perform()
    except(DHCPFailed):
        print("Unable to run DHCP for port on interface", interface)
        raise

    return port


def run_example(server_address, interface1, interface2):
    """
    This example configures a small UDP frameblasting flow with latency measurement enabled.
    :param server_address: Server to run the test on
    :param interface1: name of the first interface.  This interface will be used as source.
    :param interface2: name of the second interface.  This interfaces will be used as destination
    :return: None
    """

    byteblower_instance = ByteBlower.InstanceGet()

    # Connect to the ByteBlower server.
    server = byteblower_instance.ServerAdd(server_address)

    # create the ByteBlower Ports.  A ByteBlower port simulates a host in the network.
    port1 = initialize_port(server, interface1, mac_address="00:bb:00:00:00:01")
    port2 = initialize_port(server, interface2, mac_address="00:bb:00:00:00:02")

    # now create the stream.  A stream transmits frames on the port on which it is created.
    stream = port1.TxStreamAdd()

    # how many frames will we transmit?
    stream.NumberOfFramesSet(1000)
    # how fast must we transmit frames?
    # lets say 100 pps, so every 10ms
    # The unit is in nanoseconds, so 10ms = 10000000ns
    stream.InterFrameGapSet(10000000)

    # so the Stream will send 1000 frames at 100pps

    # a stream transmits frames, so we need to tell the stream which frames we want to transmit
    frame = stream.FrameAdd()

    # collect the frame header info.  We need to provide the Layer2 (ethernet) and Layer3 (IPv4) addresses.
    srcIp = port1.Layer3IPv4Get().IpGet()
    srcMac = port1.Layer2EthIIGet().MacGet()

    dstIp = port2.Layer3IPv4Get().IpGet()

    # the destination MAC is the MAC address of the destination port if the destination port is in the same
    # subnet as the source port, otherwise it will be the MAC address of the gateway.
    # ByteBlower has a function to resolve the correct MAC address in the Layer3 configuration object
    dstMac = port1.Layer3IPv4Get().Resolve(dstIp)

    frame_bytes = create_frame_ipv4_udp(dstMac, srcMac,
                                        dstIp, srcIp,
                                        dstUdpPort=10000, srcUdpPort=11000,
                                        length=512)
    frame.BytesSet(frame_bytes)

    # Enable latency for this frame.  The frame frame contents will be altered so it contains a timestamp.
    frame_tag = frame.FrameTagTimeGet()
    frame_tag.Enable(True)

    # create a latency-enabled trigger.  A trigger is an object which receives data.
    # The Basic trigger just count packets, a LatencyBasic trigger analyzes the timestamps embedded in the
    # received frame.
    latency_trigger = port2.RxLatencyBasicAdd()

    # every trigger needs to know on which frames it will work.  The default filter is no filter, so it will
    # analyze every frame, which is not what we want here.
    # We will filter on the destination IP and the destination UDP port
    filter = "ip dst {} and udp port 10000".format(dstIp)
    latency_trigger.FilterSet(filter)

    # print the configuration, this makes it easy to review what we have done until now
    print("Current ByteBlower configuration:")
    print("port1:", port1.DescriptionGet())
    print("port2:", port2.DescriptionGet())

    # start the traffic, clear the latency trigger.  Triggers are active as soon they are created, so
    # we may want to clear the data it already has collected.
    print("Starting traffic")
    latency_trigger.ResultClear()
    stream_history = stream.ResultHistoryGet()
    trigger_history = latency_trigger.ResultHistoryGet()

    stream.Start()

    for iteration in range(1, 10):
        # sleep one second
        sleep(1)

        # Refresh the history, the ByteBlower server will create interval and cumulative results every
        # second (by default).  The Refresh method will synchronize the server data with the client.
        stream_history.Refresh()
        trigger_history.Refresh()

        last_interval_tx = stream_history.IntervalLatestGet()
        last_interval_rx = trigger_history.IntervalLatestGet()

        print("Sent {TX} frames, received {RX} frames, average latency {LATENCY}".format(
            TX=last_interval_tx.PacketCountGet(),
            RX=last_interval_rx.PacketCountGet(),
            LATENCY=last_interval_rx.LatencyAverageGet()
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
    latency_result = latency_trigger.ResultGet()
    stream_result.Refresh()
    latency_result.Refresh()

    print("Sent {TX} frames, received {RX} frames".format(
        TX=stream_result.PacketCountGet(), RX=latency_result.PacketCountGet()
    ))
    print("Latency (Average, minimum, maximum, jitter): {AVG}ns, {MIN}ns, {MAX}ns, {JIT}ns".format(
        AVG=latency_result.LatencyAverageGet(),
        MIN=latency_result.LatencyMinimumGet(),
        MAX=latency_result.LatencyMaximumGet(),
        JIT=latency_result.JitterGet()
    ))

    # It is considered good practice to clean up your objects.  This tells the ByteBlower server it can
    # clean up its resources.
    server.PortDestroy(port1)
    server.PortDestroy(port2)

    # Disconnect from the ByteBlower server
    byteblower_instance.ServerRemove(server)


if __name__ == '__main__':
    server_address = "byteblower-tp-2100.lab.byteblower.excentis.com"
    interface1 = "trunk-1-13"
    interface2 = "trunk-1-14"

    run_example(server_address, interface1, interface2)
