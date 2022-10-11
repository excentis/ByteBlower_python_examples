"""
Basic IPv6 multicast example using the ByteBlower Python API.

Copyright 2022, Excentis N.V.
"""

from __future__ import print_function

import ipaddress
from time import sleep

import byteblowerll.byteblower
from byteblowerll.byteblower import ByteBlower
from byteblowerll.byteblower import MulticastSourceFilter
from byteblowerll.byteblower import StringList

configuration = {
    # Address (IP or FQDN) of the ByteBlower server to use
    'server_address': 'byteblower-tp-3100.lab.byteblower.excentis.com',

    # Configuration for the sender ByteBlower port.
    'tx_port_config': {
        'interface': 'trunk-1-13',
        'mac': '00:bb:01:00:00:01',
        # IP configuration for the ByteBlower Port.
        # Options are 'DHCPv6', 'SLAAC', 'static'
        # if DHCPv6, use "dhcpv6"
        'ip': 'dhcpv6',
        # if SLAAC, use "slaac"
        # 'ip': 'slaac',
        # if staticv6, use ["ipaddress", prefixlength]
        # 'ip': ['3000:3128::24', '64'],
    },

    # Configuration for the receiver ByteBlower port.
    'rx_port_config': {
        'interface': 'trunk-1-19',
        'mac': '00:bb:01:00:00:02',
        # IP configuration for the ByteBlower Port.
        # Options are 'DHCPv6', 'SLAAC', 'static'
        # if DHCPv6, use "dhcpv6"
        'ip': 'dhcpv6',
        # if SLAAC, use "slaac"
        # 'ip': 'slaac',
        # if staticv6, use ["ipaddress", prefixlength]
        # 'ip': ['3000:3128::24', '64'],
    },

    # Size of the frames to be sent (without CRC).
    # Unit: Bytes
    'frame_size': 512,

    # Sending 100 frames per second
    'interframegap_nanoseconds': 10000000,  # 10ms

    # Send traffic for 5 minutes (TODO: Change back to to 300 * 100)
    'number_of_frames': 10 * 100,

    # The multicast IP address that is used for this test.
    'multicast_ip': "ff05:0000:0000:0000:0000:0000:0002:0001"
    #'multicast_ip': "FF05:0:0:0:0:0:2:0001"

}


class Example:
    def __init__(self, **kwargs):
        self.server_address = kwargs['server_address']
        self.tx_port_config = kwargs['tx_port_config']
        self.rx_port_config = kwargs['rx_port_config']

        self.number_of_frames = kwargs['number_of_frames']
        self.frame_size = kwargs['frame_size']

        self.interframegap_ns = kwargs['interframegap_nanoseconds']

        self.multicast_ip = kwargs['multicast_ip']

        self.server = None
        self.bbport_tx = None
        self.bbport_rx = None
        self.bbport_multicast_client = None

    def cleanup(self):
        """Clean up the created objects"""
        byteblower_instance = ByteBlower.InstanceGet()
        if self.bbport_tx:
            self.server.PortDestroy(self.bbport_tx)
            self.bbport_tx = None

        if self.bbport_rx:
            self.server.PortDestroy(self.bbport_rx)
            self.bbport_rx = None

        if self.server is not None:
            byteblower_instance.ServerRemove(self.server)
            self.server = None

    def run(self):
        udp_src_port = 5001
        udp_dst_port = 5002

        byteblower_instance = ByteBlower.InstanceGet()

        print("Connecting to ByteBlower server %s..." % self.server_address)
        self.server = byteblower_instance.ServerAdd(self.server_address)

        # Create the sending port
        print("Creating TX port")
        self.bbport_tx = self.provision_port(self.tx_port_config)

        print("Creating RX port")
        self.bbport_rx = self.provision_port(self.rx_port_config)

        # Configure the flow
        src_ip = self.tx_port_config['ip_address']
        src_mac = self.bbport_tx.Layer2EthIIGet().MacGet()
        dst_ip = self.multicast_ip
        dst_mac = self.convert_multicast_ip_to_mac(dst_ip)

        print("src_ip: {}".format(src_ip))
        print("dst_ip: {}".format(dst_ip))
        print("src_mac: {}".format(src_mac))
        print("dst_mac: {}".format(dst_mac))

        # Create the stream
        stream = self.bbport_tx.TxStreamAdd()
        stream.NumberOfFramesSet(self.number_of_frames)
        stream.InterFrameGapSet(self.interframegap_ns)
        frame = stream.FrameAdd()
        frame.BytesSet(self.generate_frame_string(src_mac, src_ip, udp_src_port, dst_mac, dst_ip, udp_dst_port))

        # Create the trigger (receiver)
        trigger = self.bbport_rx.RxTriggerBasicAdd()
        filter = "ip6 dst {} and udp dst port {}".format(dst_ip, udp_dst_port)
        print("filter: {}".format(filter))
        trigger.FilterSet(filter)

        # print the configuration.
        # his makes it easy to review what we have done until now
        print("Current ByteBlower configuration:")
        print("port1:", self.bbport_tx.DescriptionGet())
        print("port2:", self.bbport_rx.DescriptionGet())

        # start the traffic and clear the trigger.
        # Triggers are active as soon they are created, so we may want to clear
        # the data it already has collected.
        print("Starting traffic")
        trigger.ResultClear()
        stream_history = stream.ResultHistoryGet()
        trigger_history = trigger.ResultHistoryGet()

        stream.Start()

        # Create MLDv2 session that listens to the multicast IP.
        mld = self.bbport_rx.Layer3IPv6Get().ProtocolMldGet()
        mld_session = mld.SessionV2Add(self.multicast_ip)

        # Create an "exclude" filter for the multicast source IPs.
        # We're using an empty filter to accept all IP sources.
        exclude_sources = StringList()
        # To exclude certain source IPs use:
        #  exclude_sources.push_back("3000:3128::24")  # Exclude "3000:3128::24"
        # ...
        # Start listening. Note it may take a few seconds before
        # we start receiving the multicast packets!
        mld_session.MulticastListen(MulticastSourceFilter.Exclude, exclude_sources)

        # Example for multicast listen with "include" filter:
        # include_sources = StringList()
        # include_sources.push_back(src_ip)
        # ...
        # mld_session.MulticastListen(MulticastSourceFilter.Include, include_sources)
        #
        # To stop listening, use an "include" command with an empty source list:
        #  mld_session.MulticastListen(MulticastSourceFilter.Include, StringList())

        duration_ns = self.interframegap_ns * self.number_of_frames
        duration_s = duration_ns / 1000000000 + 1
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

        # Get the session info for the MLD stats
        mld_session_info = mld_session.SessionInfoGet()
        mld_session_info.Refresh()
        print("MLD statistics:", mld_session_info.DescriptionGet())

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

    def generate_frame_string(self, src_mac, src_ip, udp_src_port, dst_mac, dst_ip, udp_dst_port):
        ethernet_header_len = 14
        ip_header_len = 20
        udp_header_len = 8
        total_header_len = ethernet_header_len + ip_header_len + udp_header_len
        payload = 'a' * (self.frame_size - total_header_len)

        from scapy.layers.inet6 import UDP, IPv6, Ether
        from scapy.all import Raw
        udp_payload = Raw(payload.encode('ascii', 'strict'))
        udp_header = UDP(dport=udp_dst_port, sport=udp_src_port)
        ip_header = IPv6(src=src_ip, dst=dst_ip)
        eth_header = Ether(src=src_mac, dst=dst_mac)
        scapy_frame = eth_header / ip_header / udp_header / udp_payload

        frame_content = bytearray(bytes(scapy_frame))

        # The ByteBlower API expects an 'str' as input for the
        # frame::BytesSet() method, we need to convert the bytearray
        return ''.join((format(b, "02x") for b in frame_content))

    # Converts a multicast IPv6 to a multicast MAC address.
    # For example "ff05:0000:0000:0000:0000:0000:0002:0001," will become "33:33:00:02:00:01"
    # This function expects a valid IPv6 address to be passed!
    @staticmethod
    def convert_multicast_ip_to_mac(ip_str):
        ip = ipaddress.IPv6Address(ip_str).exploded
        digits = []
        for part in ip.split(':'):
            digits.append(int("0x{}".format(part[0:2]), base=16))
            digits.append(int("0x{}".format(part[2:4]), base=16))

        print("ip: {}, digits: {}".format(ip, digits))
        return "33:33:{:02x}:{:02x}:{:02x}:{:02x}".format(digits[12], digits[13], digits[14], digits[15])


# When this python module is called stand-alone, the run-function must be
# called.  This approach makes it possible to include it in a series of
# examples.
if __name__ == "__main__":
    example = Example(**configuration)
    try:
        example.run()
    finally:
        example.cleanup()
