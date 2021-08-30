"""
  This example adds all traffic types together into a single example.
  For educational value, we do suggest to look first into the 
  the other examples for more details.
"""
from __future__ import print_function

import datetime
import math
import random
import sys
import time
from collections import defaultdict

from byteblowerll.byteblower import ByteBlower, DeviceStatus
from byteblowerll.byteblower import ParseHTTPRequestMethodFromString

from scapy.layers.inet import UDP, IP, Ether
from scapy.all import Raw

configuration = {
    # Address (IP or FQDN) of the ByteBlower server to use
    #'server_address': 'byteblower-tutorial-3100.lab.byteblower.excentis.com',
    "server_address": "10.10.1.203",
    # Interface on the server to create a port on.
    "server_interface": "nontrunk-1",
    "server_interface": "trunk-1-3",
    # MAC address of the ByteBlower port which will be generated
    "port_mac_address": "00:bb:01:00:00:01",
    # DHCP or IP configuration for the ByteBlower port
    # if DHCP, use "dhcp"
    "port_ip_address": "dhcp",
    # if static, use ["ipaddress", "netmask", "gateway"]
    # 'port_ip_address': ['172.16.0.4', '255.255.252.0', '172.16.0.1'],
    # Address (IP or FQDN) of the ByteBlower MeetingPoint to use.  The wireless
    # endpoint *must* be registered on this meeting point.
    # Special value: None.  When the address is set to None, the server_address
    #                       will be used.
    "meetingpoint_address": None,
    # UUID of the ByteBlower WirelessEndpoint to use.  This wireless endpoint
    # *must* be registered to the meetingpoint  configured by
    # meetingpoint_address.
    # Special value: None.  When the UUID is set to None, the example will
    #                       automatically select the first available wireless
    #                       endpoint.
    "wireless_endpoint_uuid": None,

    # Configures the traffic patterns to be used.
    # There's no limit on the number of such patterns. The current list
    # show all the possible configurations.
    "traffic": [
        {"type": "tcp", "http_method": "GET", "duration": 10 * 10 ** 9},
        {"type": "tcp", "http_method": "PUT", "duration": 10 * 10 ** 9},
        {
            "type": "udp",
            "direction": "up",
            "framesize": 1024,
            "bitspeed": 2e6,
            "duration": 10 * 10 ** 9,
        },
        {
            "type": "udp",
            "direction": "down",
            "framesize": 512,
            "bitspeed": 1e6,
            "duration": 10 * 10 ** 9,
        },
    ],
}


class TCPTraffic:
    """
    Minimal class for TCP traffic.
    For a more detailed example we refer
    to ipv4_tcp.py
    """

    def __init__(self, wep_port, bb_port, traffic_config):
        self.http_server = bb_port.ProtocolHttpServerAdd()
        self.http_client = wep_port.ProtocolHttpClientAdd()

        self.http_server.Start()

        server_ip = bb_port.Layer3IPv4Get().IpGet()
        tcp_server_port = self.http_server.PortGet()

        self.http_client.RemoteAddressSet(server_ip)
        self.http_client.RemotePortSet(tcp_server_port)

        traffic_duration = traffic_config.get("duration", 0)
        http_method = ParseHTTPRequestMethodFromString(
            traffic_config.get("http_method", "GET")
        )
        self.http_client.RequestDurationSet(int(traffic_duration))
        self.http_client.HttpMethodSet(http_method)

    def gather_results(self):
        result = {"bytecount": 0, "duration": 0, "bitspeed": 0}

        start_moment = float("inf")
        end_moment = float("-inf")
        for client in self.http_server.ClientIdentifiersGet():
            session = self.http_server.HttpSessionInfoGet(client)
            session_result = session.ResultHistoryGet().CumulativeLatestGet()
            result["bytecount"] += max(
                session_result.RxByteCountTotalGet(),
                session_result.TxByteCountTotalGet(),
            )
            start_moment = min(
                session_result.RxTimestampFirstGet(),
                session_result.TxTimestampFirstGet(),
                start_moment,
            )
            end_moment = max(
                session_result.RxTimestampLastGet(),
                session_result.TxTimestampLastGet(),
                end_moment,
            )

        if start_moment < float("inf") and end_moment > float("-inf"):
            result["duration"] = end_moment - start_moment
            result["bitspeed"] = 8 * result["bytecount"] * 1e9 / result["duration"]
        return result


class UDPTraffic:
    """
    Main abstractions for UDP Frameblasting.
    The child classes wil implment traffic in either
    direction.

    As can be read from the implementation, the
    main difference between up- and down lies in configuring
    the traffic.

    """

    next_free_UDP_port = 4096
    lower_layer_overhead = 14 + 20 + 8  # MAC + IPv4 + UDP

    @staticmethod
    def free_udp():
        """
        Helper method to retrieve the next free UDP port.
        This is an important part when working with the
        Wireless Endpoints.
        Unlike the ByteBlower Server, every trigger
        and every stream requires a different UDP Port.
        """
        current = UDPTrafficUp.next_free_UDP_port
        UDPTrafficUp.next_free_UDP_port += 1

        if UDPTrafficUp.next_free_UDP_port >= 2 ** 16:
            UDPTrafficUp.next_free_UDP_port = 4096
        return current

    @staticmethod
    def speed_to_ifg(bit_speed, frame_size):
        """Utility method to convert to an interframe gap"""
        return int(1e9 * 8 * frame_size / bit_speed)

    def gather_results(self):
        """
        Resultgathering is similar for both
           - Wireless Endpoint (TriggerBasicMobile and StreamMobile)
           - ByteBlower server (TriggerBasic and Stream)

        This is epecially true when processing results only
        after the testrun finishes.

        In the method below only the cumulative results
        are retrieved. To check how the over-time results
        work we suggest to look at
          - ipv4_udp_up.py
          - ipv4_udp_down.py
        """
        stream_history = self.stream.ResultHistoryGet()
        trigger_history = self.trigger.ResultHistoryGet()

        stream_history.Refresh()
        trigger_history.Refresh()

        result = {"bytecount": 0, "duration": 0, "bitspeed": 0}
        rx_cumulative = trigger_history.CumulativeLatestGet()
        tx_cumulative = stream_history.CumulativeLatestGet()
        result["bytecount"] = rx_cumulative.ByteCountGet()
        if result["bytecount"] > 0:
            rx_duration = (
                rx_cumulative.TimestampLastGet() - rx_cumulative.TimestampFirstGet()
            )
            tx_duration = (
                tx_cumulative.TimestampLastGet() - tx_cumulative.TimestampFirstGet()
            )
            result["duration"] = min(rx_duration, tx_duration)
            result["bitspeed"] = 8 * result["bytecount"] * 1e9 / result["duration"]

        return result


class UDPTrafficDown(UDPTraffic):
    """ 
        Implements traffic 
             - transmitted by an ByteBlower port,
             - received by a Wireless Endpoint.

        For a more indepth implementation we refer to
        ipv4_udp_down.py
    """
    def __init__(self, wep_port, bb_port, traffic_config):
        current_port = self.free_udp()

        # Configure the ByteBlower server to stream out the UDP traffic.
        self.stream = bb_port.TxStreamAdd()
        total_size = traffic_config.get("framesize", 1024)
        src_ip = bb_port.Layer3IPv4Get().IpGet()
        dst_ip = wep_port.DeviceInfoGet().NetworkInfoGet().IPv4Get()

        src_mac = bb_port.Layer2EthIIGet().MacGet()
        dst_mac = bb_port.Layer3IPv4Get().Resolve(dst_ip)

        udp_header = UDP(dport=current_port, sport=current_port)
        ip_header = IP(src=src_ip, dst=dst_ip)
        eth_header = Ether(src=src_mac, dst=dst_mac)
        scapy_frame = (
            eth_header
            / ip_header
            / udp_header
            / ("a" * (total_size - self.lower_layer_overhead))
        )

        frame_content = bytearray(bytes(scapy_frame))
        hexbytes = "".join(format(b, "02x") for b in frame_content)

        frame = self.stream.FrameAdd()
        frame.BytesSet(hexbytes)

        bit_speed = traffic_config.get("bitspeed", 1e6)
        duration_s = traffic_config.get("duration", 1e9) / 1e9
        self.stream.InterFrameGapSet(UDPTrafficUp.speed_to_ifg(bit_speed, total_size))

        frame_count = duration_s * (bit_speed / 8) / total_size
        self.stream.NumberOfFramesSet(int(frame_count))
        self.stream.ResultHistoryGet().SamplingBufferLengthSet(int(duration_s) + 20)

        # Configure the trigger at the Wireless Endpont. 
        self.trigger = wep_port.RxTriggerBasicAdd()
        trigger_duration = 1e9 * (duration_s + 2)

        self.trigger.DurationSet(int(trigger_duration))
        self.trigger.FilterUdpSourcePortSet(current_port)
        self.trigger.FilterUdpDestinationPortSet(current_port)
        self.trigger.FilterSourceAddressSet(src_ip)


class UDPTrafficUp(UDPTraffic):
    """ 
        Implements traffic 
             - transmitted by a Wireless Endpoint
             - received by a ByteBlower Port 

        For a more indepth implementation we refer to
        ipv4_udp_up.py
    """
    def __init__(self, wep_port, bb_port, traffic_config):
        current_port = self.free_udp()
        self.stream = wep_port.TxStreamAdd()

        total_size = traffic_config.get("framesize", 1024)
        lower_layer_overhead = 14 + 20 + 8  # MAC + IPv4 + UDP
        payload = "a" * (total_size - lower_layer_overhead)
        hexbytes = "".join((format(ord(b), "02x") for b in payload))
        frame = self.stream.FrameAdd()
        frame.PayloadSet(hexbytes)

        bit_speed = traffic_config.get("bitspeed", 1e6)
        duration_s = traffic_config.get("duration", 1e9) / 1e9
        self.stream.InterFrameGapSet(UDPTrafficUp.speed_to_ifg(bit_speed, total_size))

        frame_count = duration_s * (bit_speed / 8) / total_size
        self.stream.NumberOfFramesSet(int(frame_count))

        destination_ipv4 = bb_port.Layer3IPv4Get().IpGet()
        self.stream.DestinationAddressSet(destination_ipv4)
        self.stream.DestinationPortSet(current_port)
        self.stream.SourcePortSet(current_port)

        self.trigger = bb_port.RxTriggerBasicAdd()
        self.trigger.FilterSet("ip and udp dst port {}".format(current_port))
        self.trigger.ResultHistoryGet().SamplingBufferLengthSet(int(duration_s) + 20)


class Example:
    def __init__(self, **kwargs):
        self.server_address = kwargs["server_address"]
        self.server_interface = kwargs["server_interface"]
        self.port_mac_address = kwargs["port_mac_address"]
        self.port_ip_address = kwargs["port_ip_address"]

        self.meetingpoint_address = kwargs["meetingpoint_address"]
        if self.meetingpoint_address is None:
            self.meetingpoint_address = self.server_address

        self.wireless_endpoint_uuid = kwargs["wireless_endpoint_uuid"]
        self.traffic = kwargs["traffic"]

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
        if type(self.port_ip_address) is str and self.port_ip_address == "dhcp":
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
        self.wireless_endpoint = self.meetingpoint.DeviceGet(
            self.wireless_endpoint_uuid
        )
        self.wireless_endpoint.Lock(True)

        device_info = self.wireless_endpoint.DeviceInfoGet()

        # The network monitor is part of scenario.
        self.wireless_endpoint.Lock(True)

        # Add the monitor to the scenario.
        # The Wi-Fi statistics are captured as soon as the scenario starts.
        monitor = device_info.NetworkInfoMonitorAdd()

        traffic_flows = []
        for traffic_config in self.traffic:
            traffic_type = traffic_config["type"]
            if "tcp" == traffic_type:
                traffic_flows.append(
                    TCPTraffic(self.wireless_endpoint, self.port, traffic_config)
                )
            elif "udp" == traffic_type and "up" == traffic_config["direction"]:
                traffic_flows.append(
                    UDPTrafficUp(self.wireless_endpoint, self.port, traffic_config)
                )
            elif "udp" == traffic_type and "down" == traffic_config["direction"]:
                traffic_flows.append(
                    UDPTrafficDown(self.wireless_endpoint, self.port, traffic_config)
                )

        try:
            self.wireless_endpoint.Prepare()
            starttime = self.wireless_endpoint.Start()
            wait_time_ns = starttime - self.meetingpoint.TimestampGet()
            time.sleep(max(0, wait_time_ns / 1e9))
        except Exception as e:
            print("Error couldn't start the WE")
            print(str(e))
            sys.exit(-1)

        print("Starting the ByteBlower")
        self.port.Start()

        # Wait until the device returns.
        # As long the device is running, the device will be in
        # - DeviceStatus_Starting
        # - DeviceStatus_Running
        # As soon the device has finished the test, it will return to
        # 'DeviceStatus_Reserved', since we have a Lock on the device.
        status = self.wireless_endpoint.StatusGet()
        start_moment = datetime.datetime.now()
        while status != DeviceStatus.Reserved:
            time.sleep(1)
            status = self.wireless_endpoint.StatusGet()
            now = datetime.datetime.now()

        # Wireless Endpoint has returned. Collect and process the results.
        self.wireless_endpoint.ResultGet()
        traffic_results = []
        for config, flow in zip(self.traffic, traffic_flows):
            flow_result = flow.gather_results()
            flow_result["config"] = config
            traffic_results.append(flow_result)

        monitor_history = monitor.ResultHistoryGet()
        monitor_history.Refresh()
        monitor_results = []
        for sample in monitor_history.IntervalGet():
            current_sample = {"timestamp": sample.TimestampGet()}
            nics = []
            for network_interface in sample.InterfaceGet():
                current = {
                    "name": network_interface.DisplayNameGet(),
                    "Ssid": network_interface.WiFiSsidGet(),
                    "BSSID": network_interface.WiFiBssidGet(),
                    "Channel": network_interface.WiFiChannelGet(),
                    "RSSI": network_interface.WiFiRssiGet(),
                    "TxRate": network_interface.WiFiTxRateGet(),
                }
                nics.append(current)
            current_sample["interfaces"] = nics
            monitor_results.append(current_sample)

        # Cleanup
        self.server.PortDestroy(self.port)
        self.wireless_endpoint.Lock(False)
        return {"traffic": traffic_results, "networkinfo": monitor_results}

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


if __name__ == "__main__":
    example = Example(**configuration)
    try:
        results = example.run()
        print(results)
    finally:
        example.cleanup()
