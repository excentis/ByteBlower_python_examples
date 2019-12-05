"""
This examples builds on the basic IPv4 example, we show here 
extra how to (optionally) configure a VLAN at transmitting 
and receiving end. As is often the case, both sides can 
have a different config.

The goal of the script is to teach the impact of the VLAN on various parts of
the code. We do suggest to first get familiar with the basic IPv4
example, because as you'll notice, most is the same.

For simplicity we won't show VLAN stacks (i.e. VLANs embedded in
another VLAN). It's a small addition, we do suggest 
to try it yourself, but don't hesitate to contact us at
support.byteblower@excentis.com for help.

Copyright 2019, Excentis N.V.
"""

from __future__ import print_function
from byteblowerll.byteblower import ByteBlower

from time import sleep

configuration = {
    # Address (IP or FQDN) of the ByteBlower server to use
    'server_address': 'byteblower-tp-1300.lab.byteblower.excentis.com',

    # Configuration for the first ByteBlower port.  Will be used as the TX port.
    'port_1_config': {
        'interface': 'trunk-1-19',
        'mac': '00:bb:01:00:00:01',

        # If this port requires a VLAN, add it as as follows.
        # 'vlan': 10
        'vlan': 2,

        # IP configuration for the ByteBlower Port.  Only IPv4 is supported
        # Options are 'DHCPv4', 'static'
        # if DHCPv4, use "dhcpv4"
        'ip': 'dhcpv4',
        # if staticv4, use ["ipaddress", netmask, gateway]
        # 'ip': ['192.168.0.2', "255.255.255.0", "192.168.0.1"],
    },

    # Configuration for the second ByteBlower port.  Will be used as RX port.
    'port_2_config': {
        'interface': 'trunk-1-20',
        'mac': '00:bb:01:00:00:02',

        # VLAN can be configured optionally.
        'vlan': 2,
        # IP configuration for the ByteBlower Port.  Only IPv4 is supported
        # Options are 'DHCPv4', 'static'
        # if DHCPv4, use "dhcpv4"
        #'ip': 'static',
        # if staticv4, use ["ipaddress", netmask, gateway]
        'ip': ['172.24.107.130', "255.252.0.0", "172.24.0.1"],
    },

    # number of frames to send.
    'number_of_frames': 10000,

    # Inter frame gap to use in nanoseconds.
    # example: 1000000ns is 1ms, which is 1000pps
    'interframegap_nanoseconds': 1000000
}


class Example:
    def __init__(self, **kwargs):
        self.server_address = kwargs['server_address']
        self.port_1_config = kwargs['port_1_config']
        self.port_2_config = kwargs['port_2_config']

        self.number_of_frames = kwargs['number_of_frames']
        self.interframegap_ns = kwargs['interframegap_nanoseconds']

        self.server = None
        self.port_1 = None
        self.port_2 = None

    def run(self):
        byteblower_instance = ByteBlower.InstanceGet()

        print("Connecting to ByteBlower server {}...".format(
            self.server_address))
        self.server = byteblower_instance.ServerAdd(self.server_address)

        print("Creating ports")
        # Do check the provision_port code. The vlan has
        # a small impact there.
        self.port_1 = self.provision_port(self.port_1_config)
        self.port_2 = self.provision_port(self.port_2_config)

        # Creating the stream where we'll sent the traffic from.
        # Most is the same as the basic IPv4 example.
        stream = self.port_1.TxStreamAdd()
        stream.NumberOfFramesSet(self.number_of_frames)
        stream.InterFrameGapSet(self.interframegap_ns)

        frame = stream.FrameAdd()

        # Collect the basic addressing info for the Tx side.
        # VLAN id handled lower in the code.
        src_ip = self.port_1_config['ip_address']
        src_mac = self.port_1.Layer2EthIIGet().MacGet()

        dst_ip = self.port_2_config['ip_address']
        dst_mac = self.port_1.Layer3IPv4Get().Resolve(dst_ip)

        frame_size = 512
        udp_src = 4096
        udp_dest = 4096
        payload = 'a' * (frame_size - 42)

        from scapy.layers.inet import UDP, IP, Ether
        from scapy.all import Raw

        # We will need to add a VLAN layer in the frame to transmit.
        # In scapy Vlans are represented in the Dot1Q class.
        from scapy.all import Dot1Q

        scapy_udp_payload = Raw(payload.encode('ascii', 'strict'))
        scapy_udp_header = UDP(dport=udp_dest, sport=udp_src)
        scapy_ip_header = IP(src=src_ip, dst=dst_ip)

        # A stream will always send the packet just as configured.
        # When the Tx ByteBlower port has a VLAN, we need to add it
        # to frame to be sent.
        # The following 5 lines are the only difference compared
        # to the basic IPv4 example.
        if 'vlan' in self.port_1_config:
            vlan_id = self.port_1_config['vlan']
            scapy_frame = Ether(
                src=src_mac, dst=dst_mac) / Dot1Q(
                    vlan=vlan_id
                ) / scapy_ip_header / scapy_udp_header / scapy_udp_payload
        else:
            scapy_frame = Ether(
                src=src_mac, dst=dst_mac
            ) / scapy_ip_header / scapy_udp_header / scapy_udp_payload

        # As noted above, the remaineder of the stream config is the same again.
        frame_content = bytearray(bytes(scapy_frame))
        hexbytes = ''.join((format(b, "02x") for b in frame_content))
        frame.BytesSet(hexbytes)

        # create a trigger to count the number of received frames.
        # Similar to the stream we will need to make a slight modification
        # for the Vlan layer.
        trigger = self.port_2.RxTriggerBasicAdd()

        # The BPF filter on a trigger is promiscous: it will be applied to all
        # traffic that arrives at the Physical interface.
        #
        # When we expect to receive packets with a VLAN, we need to add
        # this element to the filter.
        if 'vlan' in self.port_2_config:
            rx_vlan_id = str(self.port_2_config['vlan'])
            bpf_filter = "vlan {} and ip dst {} and udp port {}".format(
                rx_vlan_id, dst_ip, udp_dest)
        else:
            bpf_filter = "ip dst {} and udp port {}".format(dst_ip, udp_dest)
        trigger.FilterSet(bpf_filter)

        # The above filter was the last change necessary in this method. The remainder,
        #  result gathering and cleanup is the same.

        # VLAN info will be list in the port description below.
        print("Current ByteBlower configuration:")
        print("port1:", self.port_1.DescriptionGet())
        print("port2:", self.port_2.DescriptionGet())

        print("Starting traffic")
        trigger.ResultClear()
        stream_history = stream.ResultHistoryGet()
        trigger_history = trigger.ResultHistoryGet()

        duration_ns = self.interframegap_ns * self.number_of_frames
        duration_s = duration_ns / 1000000000 + 1

        # Running the test. No difference here.
        # For more info on specific methods, do look into
        # the API specification (http:\\api.byteblower.com)
        # or the ipv4.py example.
        stream.Start()
        for iteration in range(1, int(duration_s)):
            sleep(1)

            stream_history.Refresh()
            trigger_history.Refresh()

            last_interval_tx = stream_history.IntervalLatestGet()
            last_interval_rx = trigger_history.IntervalLatestGet()

            print("Sent {TX} frames, received {RX} frames".format(
                TX=last_interval_tx.PacketCountGet(),
                RX=last_interval_rx.PacketCountGet()))

        print("Done sending traffic (time elapsed)")

        print("Waiting for a second")
        sleep(1)

        # Collect and show the results.
        stream_result = stream.ResultGet()
        oos_result = trigger.ResultGet()
        stream_result.Refresh()
        print("Stream result:", stream_result.DescriptionGet())
        oos_result.Refresh()
        print("Out of sequence result:", oos_result.DescriptionGet())

        tx_frames = stream_result.PacketCountGet()
        rx_frames = oos_result.PacketCountGet()

        print("Sent {TX} frames, received {RX} frames".format(
            TX=tx_frames, RX=rx_frames))

        # No specific cleanup is needed for the Vlan.
        self.server.PortDestroy(self.port_1)
        self.server.PortDestroy(self.port_2)
        byteblower_instance.ServerRemove(self.server)

        return [tx_frames, rx_frames]

    def provision_port(self, config):
        """
            Applies the config parameter to a ByteBlower port.

            Little has changed in this example compared to 
            IPv4.py. For the generic info we suggest to 
            look there.

            The VLAN config is new. As you'll notice this is 
            only a small part of the config.
        """
        port = self.server.PortCreate(config['interface'])
        port_l2 = port.Layer2EthIISet()
        port_l2.MacSet(config['mac'])

        # When the config has vlan, add this
        # layer to the ByteBlower port.
        # The extra layer ensures that the ByteBlowerPort
        # performs basic functionality (DHCP, ARP,..) in
        # the configured VLAN.
        #
        # This is the only change in this method compared
        # to ipv4.py
        if 'vlan' in config:
            vlan_id = int(config['vlan'])
            port_l2_5 = port.Layer25VlanAdd()
            port_l2_5.IDSet(vlan_id)

        # The remainder of the config is independent of a
        # VLAN config. When necessary the ByteBlower will
        # will automatically add the VLAN to the appropriate
        # protocols.
        ip_config = config['ip']
        if not isinstance(ip_config, list):
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


# When this python module is called stand-alone, the run-function must be
# called.  This approach makes it possible to include it in a series of
# examples.
if __name__ == "__main__":
    Example(**configuration).run()
