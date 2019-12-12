#!/usr/bin/python
""""
This example allows the user to configure a frameblasting flow which transmits data to the wireless endpoint.

WirelessEndpoint --> ByteBlowerPort
"""

from __future__ import print_function
# We want to use the ByteBlower python API, so import it
from byteblowerll.byteblower import ByteBlower, ConfigError

from scapy.packet import Raw
import datetime
import os


configuration = {
    # Address (IP or FQDN) of the ByteBlower server to use
    'server_address': 'byteblower-tp-2100.lab.byteblower.excentis.com',

    # Interface on the server to create a port on.
    'server_interface': 'trunk-1-1',

    # MAC address of the ByteBlower port which will be generated
    'port_mac_address': '00:bb:01:00:00:01',

    # DHCP or IP configuration for the ByteBlower port
    # if DHCP, use "dhcp"
    'port_ip_address': 'dhcp',
    # if static, use ["ipaddress", "netmask", "gateway"]
    # 'port_ip_address': ['172.16.0.4', '255.255.252.0', '172.16.0.1'],

    # Address (IP or FQDN) of the ByteBlower Meetingpoint to use.  The wireless endpoint *must* be registered
    # on this meetingpoint.
    # Special value: None.  When the address is set to None, the server_address will be used.
    'meetingpoint_address': None,

    # UUID of the ByteBlower WirelessEndpoint to use.  This wireless endpoint *must* be registered to the meetingpoint
    # configured by meetingpoint_address.
    # Special value: None.  When the UUID is set to None, the example will automatically select the first available
    # wireless endpoint.
    'wireless_endpoint_uuid': None,
    # 'wireless_endpoint_uuid': 'eda84fd1f0761a6d',
    # 'wireless_endpoint_uuid': '6d9c2347-e6c1-4eea-932e-053801de32eb',

    # Name of the WiFi interface to query.
    # Special value: None.  None will search for an interface with type WiFi.
    # 'wireless_interface': None,
    'wireless_interface': 'wlan0',

    # Size of the frame on ethernet level. Do not include the CRC
    'frame_size': 1024,

    # Number of frames per second
    'frames_per_second': 7000,

    # duration, in nanoseconds
    # Duration of the session
    #           sec  milli  micro  nano
    'duration': 30 * 1000 * 1000 * 1000,

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
        self.wireless_interface = kwargs['wireless_interface']

        self.frame_size = kwargs['frame_size']
        self.duration = kwargs['duration']
        self.interframe_gap_nanoseconds = int(1.0 * 1000 * 1000 * 1000 / kwargs['frames_per_second'])
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
        port_layer3_config = self.port.Layer3IPv4Set()
        if type(self.port_ip_address) is str and self.port_ip_address == 'dhcp':
            # DHCP is configured on the DHCP protocol
            dhcp_protocol = port_layer3_config.ProtocolDhcpGet()
            dhcp_protocol.Perform()
        else:
            # Static addressing
            port_layer3_config.IpSet(self.port_ip_address[0])
            port_layer3_config.NetmaskSet(self.port_ip_address[1])
            port_layer3_config.GatewaySet(self.port_ip_address[2])

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
        number_of_frames = int(self.duration / self.interframe_gap_nanoseconds)
        stream.NumberOfFramesSet(number_of_frames)

        # a stream needs to send some data, so lets create a frame
        # For the frame, we need:
        # - The destination IP address (The IP address of the ByteBlower port)
        # - The source and destination UDP ports (we configured this on top of this script)
        # - a payload to transmit.

        port_layer3_config = self.port.Layer3IPv4Get()
        port_ipv4 = port_layer3_config.IpGet()

        payload = 'a' * (self.frame_size - 42)

        scapy_udp_payload = Raw(payload.encode('ascii', 'strict'))

        payload_array = bytearray(bytes(scapy_udp_payload))

        # The ByteBlower API expects an 'str' as input for the Frame::BytesSet(), we need to convert the bytearray
        hexbytes = ''.join((format(b, "02x") for b in payload_array))

        frame = stream.FrameAdd()
        frame.PayloadSet(hexbytes)

        stream.DestinationAddressSet(port_ipv4)
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
        trigger.FilterSet("ip host " + port_ipv4 + " and udp port " + str(self.udp_dstport))

        # We also want the network information over time, to compare the RSSI vs the Loss
        network_info_monitor = self.wireless_endpoint.DeviceInfoGet().NetworkInfoMonitorAdd()

        # Now all configuration is made
        print(stream.DescriptionGet())
        print(trigger.DescriptionGet())
        print(network_info_monitor.DescriptionGet())

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

        duration_ns = self.duration + 1000000000
        print("Port will transmit for", duration_ns / 1000000000.0, "seconds")
        self.port.Start()

        print("Waiting for the test to finish")
        for i in range(int(duration_ns / 1000000000)):
            # Refresh the stream results
            stream.ResultHistoryGet().Refresh()

            # Refresh the trigger results
            trigger.ResultHistoryGet().Refresh()

            sleep(1)

        print("Wait for the device to beat")
        # Usually one second
        sleep(1)

        # get the results from the wireless endpoint
        self.wireless_endpoint.ResultGet()

        self.wireless_endpoint.Lock(False)

        stream_history = stream.ResultHistoryGet()
        stream_history.Refresh()
        trigger_history = trigger.ResultHistoryGet()
        trigger_history.Refresh()
        network_info_monitor_history = network_info_monitor.ResultHistoryGet()
        network_info_monitor_history.Refresh()

        results = []
        for network_info_interval in network_info_monitor_history.IntervalGet():
            timestamp = network_info_interval.TimestampGet()

            network_interface = self.find_wifi_interface(network_info_interval.InterfaceGet())

            result = {
                'timestamp': timestamp,
                'rssi': -127,
                'ssid': '',
                'bssid': '',
                'tx_frames': 0,
                'rx_frames': 0,
                'loss': 0,
                'throughput': 0
            }
            if network_interface is not None:
                result['rssi'] = network_interface.WiFiRssiGet()
                result['ssid'] = network_interface.WiFiSsidGet()
                result['bssid'] = network_interface.WiFiBssidGet()

            try:
                stream_interval = stream_history.IntervalGetByTime(timestamp)
                result['tx_frames'] = stream_interval.PacketCountGet()
            except ConfigError as e:
                print("ERROR: Could not get result for stream on timestamp", timestamp, ":", str(e))

            try:
                trigger_interval = trigger_history.IntervalGetByTime(timestamp)
                result['rx_frames'] = trigger_interval.PacketCountGet()

                throughput = self.frame_size * result['rx_frames'] * 8
                result['throughput'] = throughput
            except ConfigError as e:
                print("ERROR: Could not get result for trigger on timestamp", timestamp, ":", str(e))

            if result['tx_frames'] != 0:
                lost_frames = result['tx_frames'] - result['rx_frames']
                loss = lost_frames * 100.0 / result['tx_frames']
                result['loss'] = loss

            results.append(result)

        return results

    def cleanup(self):
        instance = ByteBlower.InstanceGet()

        # Cleanup
        if self.meetingpoint is not None:
            instance.MeetingPointRemove(self.meetingpoint)
        if self.server is not None:
            instance.ServerRemove(self.server)

    def find_wifi_interface(self, interface_list):
        """"Looks for the wireless interface
        If wireless_interface is defined and not set to None, find this
        interface
        If it is not found, look for the first interface with type
        NetworkInterfaceType_Wifi.
        Else, return None

        :param interface_list: List of interfaces to query
        :type interface_list: `byteblowerll.byteblower.NetworkInterfaceList`
        :return: the selected network interface
        :rtype: :class:`byteblowerll.byteblower.NetworkInterface`
        """
        from byteblowerll.byteblower import (NetworkInterface,
                                             NetworkInterfaceType_WiFi)

        if self.wireless_interface is not None:
            for interface in interface_list:
                assert isinstance(interface, NetworkInterface)
                if (interface.DisplayNameGet() == self.wireless_interface
                        or interface.NameGet() == self.wireless_interface):
                    return interface

        # Still here?
        # no specific interface requested or the interface was not found, so
        # just selecting the first interface with an SSID.

        for interface in interface_list:
            if (interface.TypeGet() == NetworkInterfaceType_WiFi
                    and interface.WiFiSsidGet() != ''):
                return interface

        # still here?
        # no suitable interface found, returning None
        return None

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
                print("Selecting device", device.DeviceIdentifierGet())
                return device.DeviceIdentifierGet()

            print("Not selecting device", device.DeviceIdentifierGet())
            print(device.DescriptionGet())

        # No device found, return None
        return None


def human_readable_date(bb_timestamp):
    return str(datetime.datetime.fromtimestamp(int(bb_timestamp / 1e9)))


def write_csv(result_list, filename, keys, separator=','):
    with open(filename, 'w') as f:
        # Write the headers
        f.write(separator.join(['"' + key + '"' for key in keys]) + "\n")

        # Write the results
        for result in result_list:
            items = []

            # format the result items,
            # strings will be quoted,
            # timestamps will be human readable dates
            for key in keys:
                item = result[key]

                if key == 'timestamp':
                    item = human_readable_date(int(item))

                if isinstance(item, str):
                    item = '"' + item + '"'

                items.append(str(item))

            # Write the result
            f.write(separator.join(items) + "\n")


if __name__ == '__main__':
    from plotting import rssi_plot_highcharts

    example = Example(**configuration)
    device_name = "Unknown"
    try:
        example_results = example.run()
        device_name = example.wireless_endpoint.DeviceInfoGet().GivenNameGet()

        print("Storing the results")
        results_file = os.path.basename(__file__) + ".csv"
        desired_keys = ['timestamp', 'tx_frames', 'rx_frames', 'loss', 'throughput', 'rssi', 'ssid', 'bssid']
        write_csv(example_results, filename=results_file, keys=desired_keys)
        print("Results written to", results_file)

        rssi_plot_highcharts.plot_data(device_name, results_file)

    finally:
        example.cleanup()
