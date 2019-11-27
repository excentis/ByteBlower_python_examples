#!/usr/bin/python
""""
This example allows the user to configure a frameblasting flow which transmits data to the wireless endpoint.

WirelessEndpoint --> ByteBlowerPort
"""

from __future__ import print_function
# We want to use the ByteBlower python API, so import it
from byteblowerll.byteblower import ByteBlower

from scapy.packet import Raw


configuration = {
    # Address (IP or FQDN) of the ByteBlower server to use
    'server_address': 'byteblower-tp-2100.lab.byteblower.excentis.com',

    # Interface on the server to create a port on.
    'server_interface': 'trunk-1-13',

    # MAC address of the ByteBlower port which will be generated
    'port_mac_address': '00:bb:01:00:00:01',

    # IP configuration for the ByteBlower Port.
    # Options are
    # * DHCP
    # * SLAAC
    # * static
    # if DHCP, use "dhcp"
    # 'port_ip_address': 'dhcp',
    # if SLAAC, use "slaac"
    'port_ip_address': 'slaac',
    # if static, use ["ipaddress", prefixlength]
    # 'port_ip_address': ['3000:3128::24', '64'],

    # Address (IP or FQDN) of the ByteBlower Meetingpoint to use.  The wireless endpoint *must* be registered
    # on this meetingpoint.
    # Special value: None.  When the address is set to None, the server_address will be used.
    'meetingpoint_address': None,

    # UUID of the ByteBlower WirelessEndpoint to use.  This wireless endpoint *must* be registered to the meetingpoint
    # configured by meetingpoint_address.
    # Special value: None.  When the UUID is set to None, the example will automatically select the first available
    # wireless endpoint.
    'wireless_endpoint_uuid': None,
    # 'wireless_endpoint_uuid': 'fd9d9566-8aa3-47c3-9d4b-e597362728d1',

    # Name of the traffic interface of the ByteBlower wireless endpoint.
    # only needed when the Wireless endpoint has multiple interfaces with IPv6 addresses. (e.g. The wireless endpoint
    # has an management and traffic interface.
    # 'wireless_endpoint_traffic_interface': None,
    'wireless_endpoint_traffic_interface': "eth1",

    # Size of the frame on ethernet level. Do not include the CRC
    'frame_size': 252,

    # Number of frames to send.
    'number_of_frames': 1000,

    # How fast must the frames be sent.  e.g. every 10 milliseconds (=10000000 nanoseconds)
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
        self.wireless_endpoint_traffic_interface = kwargs['wireless_endpoint_traffic_interface']

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
        instance = ByteBlower.InstanceGet()
        assert isinstance(instance, ByteBlower)

        # Connect to the server
        self.server = instance.ServerAdd(self.server_address)

        # create and configure the port.
        self.port = self.server.PortCreate(self.server_interface)

        # configure the MAC address on the port
        port_layer2_config = self.port.Layer2EthIISet()
        port_layer2_config.MacSet(self.port_mac_address)

        # configure the IP addressing on the port
        port_layer3_config = self.port.Layer3IPv6Set()
        if type(self.port_ip_address) is str and self.port_ip_address.lower() == 'dhcp':
            # DHCP is configured on the DHCP protocol
            dhcp_protocol = port_layer3_config.ProtocolDhcpGet()
            dhcp_protocol.Perform()
        elif type(self.port_ip_address) is str and self.port_ip_address.lower() == 'slaac':
            # wait for stateless autoconfiguration to complete
            port_layer3_config.StatelessAutoconfiguration()
        else:
            # Static addressing
            address = self.port_ip_address[0]
            prefixlength = self.port_ip_address[1]
            ip = "{}/{}".format(address, prefixlength)
            port_layer3_config.IpManualAdd(ip)

        print("Created port", self.port.DescriptionGet())

        # Connect to the meetingpoint
        self.meetingpoint = instance.MeetingPointAdd(self.meetingpoint_address)

        # If no WirelessEndpoint UUID was given, search an available one.
        if self.wireless_endpoint_uuid is None:
            self.wireless_endpoint_uuid = self.select_wireless_endpoint_uuid()

        # Get the WirelessEndpoint device
        self.wireless_endpoint = self.meetingpoint.DeviceGet(self.wireless_endpoint_uuid)
        print("Using wireless endpoint", self.wireless_endpoint.DescriptionGet())

        # Now we have the correct information to start configuring the flow.

        # The ByteBlower port will transmit frames to the wireless endpoint,
        # This means we need to create a 'stream' on the ByteBlower port and a Trigger on the WirelessEndpoint

        stream = self.wireless_endpoint.TxStreamAdd()
        stream.InterFrameGapSet(self.interframe_gap_nanoseconds)
        stream.NumberOfFramesSet(self.number_of_frames)

        # a stream needs to send some data, so lets create a frame
        # For the frame, we need:
        # - The destination IP address (The IP address of the ByteBlower port)
        # - The source and destination UDP ports (we configured this on top of this script)
        # - a payload to transmit.

        port_layer3_config = self.port.Layer3IPv6Get()
        ipv6_addresses = port_layer3_config.IpLinkLocalGet()
        if self.port_ip_address == "dhcp":
            ipv6_addresses = port_layer3_config.IpDhcpGet()
        elif self.port_ip_address == "slaac":
            ipv6_addresses = port_layer3_config.IpStatelessGet()
        elif isinstance(self.port_ip_address, list):
            ipv6_addresses = port_layer3_config.IpManualGet()

        port_ipv6 = None
        for ipv6_address in ipv6_addresses:
            port_ipv6 = ipv6_address.split("/")[0]

        payload = 'a' * (self.frame_size - 42)

        scapy_udp_payload = Raw(payload.encode('ascii', 'strict'))

        payload_array = bytearray(bytes(scapy_udp_payload))

        # The ByteBlower API expects an 'str' as input for the Frame::BytesSet(), we need to convert the bytearray
        hexbytes = ''.join((format(b, "02x") for b in payload_array))

        frame = stream.FrameAdd()
        frame.PayloadSet(hexbytes)

        stream.DestinationAddressSet(port_ipv6)
        stream.DestinationPortSet(self.udp_dstport)
        stream.SourcePortSet(self.udp_srcport)

        # The trigger on the WirelessEndpoint counts received frames
        # We need
        # - the source UDP port
        # - the destination UDP port
        # - the destination IP address
        trigger = self.port.RxTriggerBasicAdd()

        # Trigger on a ByteBlower port uses BPF
        # Note: We could generate a more effective filter which will only trigger the traffic,
        #       but for demo purposes and taking NAT into account, we just keep it simple.
        trigger.FilterSet("ip6 host " + port_ipv6 + " and udp port " + str(self.udp_dstport))

        # Now all configuration is made
        print(stream.DescriptionGet())
        print(trigger.DescriptionGet())

        # Make sure we are the only users for the wireless endpoint
        self.wireless_endpoint.Lock(True)

        # Upload the configuration to the wireless endpoint
        self.wireless_endpoint.Prepare()

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

        duration_ns = self.interframe_gap_nanoseconds * self.number_of_frames + 1000000000
        print("Port will transmit for", duration_ns / 1000000000.0, "seconds")
        self.port.Start()

        print("Waiting for the test to finish")
        sleep(duration_ns / 1000000000.0)

        # get the results from the wireless endpoint
        self.wireless_endpoint.ResultGet()

        self.wireless_endpoint.Lock(False)

        tx_result = stream.ResultGet()
        tx_result.Refresh()
        rx_result = trigger.ResultGet()
        rx_result.Refresh()

        print("Transmitted", tx_result.PacketCountGet(), "packets")
        print("Received   ", rx_result.PacketCountGet(), "packets")

        return {
            'tx': tx_result.PacketCountGet(),
            'rx': rx_result.PacketCountGet()
        }

    def cleanup(self):
        instance = ByteBlower.InstanceGet()

        # Cleanup
        if self.meetingpoint is not None:
            instance.MeetingPointRemove(self.meetingpoint)
        if self.server is not None:
            instance.ServerRemove(self.server)

    def select_wireless_endpoint_uuid(self):
        """
        Walk over all known devices on the meetingpoint.
        If the device has the status 'Available', return its UUID, otherwise return None
        :return: a string representing the UUID or None
        """
        from byteblowerll.byteblower import DeviceStatus_Available

        for device in self.meetingpoint.DeviceListGet():
            # is the status Available?
            if device.StatusGet() == DeviceStatus_Available:
                # yes, return the UUID
                return device.DeviceIdentifierGet()

        # No device found, return None
        return None

    def select_wireless_endpoint_addresses(self):
        """
        Search for the traffic interface on the wireless endpoint. Return all available Global IPv6 addresses
        :return: list if IPv6 addresses
        """
        device_info = self.wireless_endpoint.DeviceInfoGet()
        network_info = device_info.NetworkInfoGet()

        for network_interface in network_info.InterfaceGet():
            if network_interface.NameGet() == self.wireless_endpoint_traffic_interface:
                return [address.split('/')[0] for address in network_interface.IPv6GlobalGet()]

        return []


if __name__ == '__main__':
    example = Example(**configuration)
    try:
        example.run()
    finally:
        example.cleanup()
