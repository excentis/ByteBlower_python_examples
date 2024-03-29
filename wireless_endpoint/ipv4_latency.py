"""
Basic IPv4 with latency measurement example for the ByteBlower Python API.
All examples are garanteed to work with Python 2.7 and above

Copyright 2018, Excentis N.V.
"""

from __future__ import print_function
from byteblowerll.byteblower import ByteBlower, DeviceStatus


configuration = {
    # Address (IP or FQDN) of the ByteBlower server to use
    'server_address': 'byteblower-tutorial-3100.lab.byteblower.excentis.com',

    # Interface on the server to create a port on.
    'server_interface': 'nontrunk-1',

    # MAC address of the ByteBlower port which will be generated
    'port_mac_address': '00:bb:01:00:00:01',

    # DHCP or IP configuration for the ByteBlower port
    # if DHCP, use "dhcp"
    'port_ip_address': 'dhcp',
    # if static, use ["ipaddress", "netmask", "gateway"]
    # 'port_ip_address': ['172.16.0.4', '255.255.252.0', '172.16.0.1'],

    # Address (IP or FQDN) of the ByteBlower Meetingpoint to use.
    # The wireless endpoint *must* be registered on this meetingpoint.
    # Special value: None.  When the address is set to None,
    # the server_address will be used.
    'meetingpoint_address': None,

    # UUID of the ByteBlower WirelessEndpoint to use.
    # This wireless endpoint *must* be registered to the meetingpoint
    # configured by meetingpoint_address.
    # Special value: None.  When the UUID is set to None, the example will
    # automatically select the first available wireless endpoint.
    # 'wireless_endpoint_uuid': '65e298b8-5206-455c-8a38-6cd254fc59a2',
    'wireless_endpoint_uuid': None,

    # Size of the frame on ethernet level. Do not include the CRC
    'frame_size': 252,

    # Number of frames to send.
    'number_of_frames': 2000,

    # How fast must the frames be sent.
    # e.g. every 10 milliseconds (=10000000 nanoseconds)
    'interframe_gap_nanoseconds': 10000000,

    'udp_srcport': 4096,
    'udp_dstport': 4096,
}


class Example:
    def __init__(self, **kwargs):
        self.server_address = kwargs['server_address']
        self.server_interface = kwargs['server_interface']
        self.port_mac_address = kwargs['port_mac_address']
        self.port_ip_address = kwargs['port_ip_address']

        self.meetingpoint_address = kwargs['meetingpoint_address']
        if self.meetingpoint_address is None:
            self.meetingpoint_address = self.server_address

        self.wireless_endpoint_uuid = kwargs['wireless_endpoint_uuid']

        self.frame_size = kwargs['frame_size']
        self.number_of_frames = kwargs['number_of_frames']
        self.interframe_gap_nanoseconds = kwargs['interframe_gap_nanoseconds']
        self.udp_srcport = kwargs['udp_srcport']
        self.udp_dstport = kwargs['udp_dstport']

        self.server = None
        self.port = None
        self.meetingpoint = None
        self.wireless_endpoint = None

    def run(self):
        byteblower_instance = ByteBlower.InstanceGet()

        print("Connecting to ByteBlower server %s..." % self.server_address)
        self.server = byteblower_instance.ServerAdd(self.server_address)

        # Create the port which will be the HTTP server (port_1)
        print("Creating TX port")
        self.port = self.server.PortCreate(self.server_interface)

        # configure the MAC address on the port
        port_layer2_config = self.port.Layer2EthIISet()
        port_layer2_config.MacSet(self.port_mac_address)

        # configure the IP addressing on the port
        port_layer3_config = self.port.Layer3IPv4Set()

        if (type(self.port_ip_address) is str
                and self.port_ip_address == 'dhcp'):
            # DHCP is configured on the DHCP protocol
            dhcp_protocol = port_layer3_config.ProtocolDhcpGet()
            dhcp_protocol.Perform()
        else:
            # Static addressing
            port_layer3_config.IpSet(self.port_ip_address[0])
            port_layer3_config.NetmaskSet(self.port_ip_address[1])
            port_layer3_config.GatewaySet(self.port_ip_address[2])

        # Connect to the meetingpoint
        self.meetingpoint = byteblower_instance.MeetingPointAdd(self.meetingpoint_address)

        # If no WirelessEndpoint UUID was given, search an available one.
        if self.wireless_endpoint_uuid is None:
            self.wireless_endpoint_uuid = self.select_wireless_endpoint_uuid()

        # Get the WirelessEndpoint device
        self.wireless_endpoint = self.meetingpoint.DeviceGet(self.wireless_endpoint_uuid)
        print("Using wireless endpoint",
              self.wireless_endpoint.DescriptionGet())

        # the destination MAC is the MAC address of the destination port if
        # the destination port is in the same subnet as the source port,
        # otherwise it will be the MAC address of the gateway.
        # ByteBlower has a function to resolve the correct MAC address in
        # the Layer3 configuration object
        network_info = self.wireless_endpoint.DeviceInfoGet().NetworkInfoGet()
        wireless_endpoint_ipv4 = network_info.IPv4Get()

        port_mac = self.port.Layer2EthIIGet().MacGet()
        port_layer3_config = self.port.Layer3IPv4Get()
        port_ipv4 = port_layer3_config.IpGet()

        # destination MAC must be resolved, since we do not know whether
        # the wireless endpoint is available on the local LAN
        destination_mac = port_layer3_config.Resolve(wireless_endpoint_ipv4)

        payload = 'a' * (self.frame_size - 42)

        duration_ns = self.interframe_gap_nanoseconds * self.number_of_frames

        # Add 2 seconds of rollout, so frames in transit can be counted too
        duration_ns += 2 * 1000 * 1000 * 1000

        # create a latency-enabled trigger.  A trigger is an object which
        # receives data.  The Basic trigger just count packets,
        # a LatencyBasic trigger analyzes the timestamps embedded in the
        # received frame.
        latency_trigger = self.wireless_endpoint.RxLatencyBasicAdd()

        # configure the trigger
        latency_trigger.DurationSet(duration_ns)
        latency_trigger.FilterUdpSourcePortSet(self.udp_srcport)
        latency_trigger.FilterUdpDestinationPortSet(self.udp_dstport)
        latency_trigger.FilterSourceAddressSet(port_ipv4)

        stream = self.port.TxStreamAdd()
        stream.InterFrameGapSet(self.interframe_gap_nanoseconds)
        stream.NumberOfFramesSet(self.number_of_frames)

        from scapy.layers.inet import UDP, IP, Ether
        from scapy.all import Raw
        udp_payload = Raw(payload.encode('ascii', 'strict'))
        udp_header = UDP(dport=self.udp_dstport, sport=self.udp_srcport, chksum=0)
        ip_header = IP(src=port_ipv4, dst=wireless_endpoint_ipv4)
        eth_header = Ether(src=port_mac, dst=destination_mac)
        scapy_frame = eth_header / ip_header / udp_header / udp_payload

        frame_content = bytearray(bytes(scapy_frame))

        # The ByteBlower API expects an 'str' as input for the
        # frame.BytesSet() method, we need to convert the bytearray
        hexbytes = ''.join((format(b, "02x") for b in frame_content))

        # Since a stream transmits frames, we need to tell the stream which
        # frames we want to transmit
        frame = stream.FrameAdd()
        frame.BytesSet(hexbytes)

        # Enable latency for this frame.  The frame frame contents will be
        # altered so it contains a timestamp.
        frame_tag = frame.FrameTagTimeGet()
        frame_tag.Enable(True)

        # Make sure we are the only users for the wireless endpoint
        self.wireless_endpoint.Lock(True)

        # Upload the configuration to the wireless endpoint
        self.wireless_endpoint.Prepare()

        # print the configuration
        # This makes it easy to review what we have done until now
        print("Current ByteBlower configuration:")
        print("port:", self.port.DescriptionGet())
        print("wireless endpoint:", self.wireless_endpoint.DescriptionGet())

        # start the traffic, clear the latency trigger.  Triggers are active
        # as soon they are created, so we may want to clear the data it already
        # has collected.
        print("Starting traffic")
        latency_trigger.ResultClear()

        duration_ns = self.interframe_gap_nanoseconds * self.number_of_frames

        from time import sleep
        # POSIX timestamp in nanoseconds when the wireless endpoint will start
        starttime_posix = self.wireless_endpoint.Start()
        # Current POSIX timestamp on the meetingpoint
        current_time_posix = self.meetingpoint.TimestampGet()

        time_to_wait_ns = starttime_posix - current_time_posix
        # Wait 200 ms longer, to make sure the wireless endpoint has started.
        time_to_wait_ns += 200000000

        print("Waiting for", time_to_wait_ns / 1000000000.0, "to start the port")
        sleep(time_to_wait_ns / 1000000000.0)

        stream.Start()

        print("Waiting for the test to finish")
        sleep(duration_ns / 1000000000.0)

        print("Done sending traffic (time elapsed)")

        # Waiting for a second after the stream is finished.
        # This has the advantage that frames that were transmitted but were
        # not received yet, can be processed by the server
        print("Waiting for a second")
        sleep(1)

        # During the test itself we queried the interval counters, there are
        # also cumulative counters.  The last cumulative counter available in
        # the history is also available as the Result
        self.wireless_endpoint.ResultGet()
        stream_result = stream.ResultGet()
        latency_result = latency_trigger.ResultGet()
        stream_result.Refresh()
        latency_result.Refresh()

        tx_frames = stream_result.PacketCountGet()
        rx_frames = latency_result.PacketCountGet()
        latency_min = 0
        latency_max = 0
        latency_avg = 0
        jitter = 0
        if latency_result.PacketCountValidGet() > 0:
            latency_min = latency_result.LatencyMinimumGet()
            latency_avg = latency_result.LatencyAverageGet()
            latency_max = latency_result.LatencyMaximumGet()
            jitter = latency_result.JitterGet()

        print("Sent {TX} frames, received {RX} frames".format(TX=tx_frames, RX=rx_frames))
        print("Latency (Average, minimum, maximum, jitter): {AVG}ns, {MIN}ns, {MAX}ns, {JIT}ns".format(
            AVG=latency_avg,
            MIN=latency_min,
            MAX=latency_max,
            JIT=jitter
        ))

        # It is considered good practice to clean up your objects.  This tells the ByteBlower server it can
        # clean up its resources.
        self.server.PortDestroy(self.port)
        self.wireless_endpoint.Lock(False)

        return [tx_frames, rx_frames, latency_min, latency_avg, latency_max, jitter]

    def cleanup(self):
        instance = ByteBlower.InstanceGet()

        # Cleanup
        if self.meetingpoint is not None:
            instance.MeetingPointRemove(self.meetingpoint)
        if self.server is not None:
            instance.ServerRemove(self.server)

    def select_wireless_endpoint_uuid(self):
        """Select a suitable wireless endpoint
        Walk over all known devices on the meetingpoint.
        If the device has the status 'Available', return its UUID,
        otherwise return None
        :return: a string representing the UUID or None
        """

        for device in self.meetingpoint.DeviceListGet():
            # is the status Available?
            if device.StatusGet() == DeviceStatus.Available:
                # yes, return the UUID
                return device.DeviceIdentifierGet()

        # No device found, return None
        return None


# When this python module is called stand-alone, the run-function must be
# called.  This approach makes it possible to include it in a series of
# examples.
if __name__ == "__main__":
    example = Example(**configuration)
    try:
        output = example.run()

        print("TX: {}, RX: {}, Latency (min, avg, max, jitter) ({}, {}, {}, {})", *output)
    finally:
        example.cleanup()
