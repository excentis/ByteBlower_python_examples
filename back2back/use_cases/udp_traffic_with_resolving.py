#!/usb/bin/python
"""This example is a "full-monty" frame blasting example

It illustrates how to send UDP traffic with the following variables

- A port can be configured with STATIC IP addressing or DHCP addressing
- A port can be in a VLAN stack
- A port can be behind a NAT enabled gateway

The example sends a configurable number of 'upstream' and 'downstream' flows.
Upstream means that traffic will flow from a device (possibly behind a NAT) to
a 'public' device.  The public device is usually situated on the 'WAN' side of
the Network Under Test.
Downstream means that traffic will flow from the 'WAN' side of the Network
Under Test to the 'private' device (e.g. a CPE behind a Cable Modem...)

At the bottom of the script there are several example functions which configure
the example in a slightly different way to demonstrate what is possible
"""
import datetime
import logging
import math
import random
import time

from byteblowerll import byteblower


class Device:
    def __init__(self, **kwargs):
        self.interface = kwargs.pop('interface')

        random_mac = '00:bb:bb:%02x:%02x:%02x' % (
            random.randint(1, 255),
            random.randint(1, 255),
            random.randint(1, 255),
        )
        self.mac = kwargs.pop('mac', random_mac)

        vlan = kwargs.pop('vlan', None)
        vlans = kwargs.pop('vlans', [])
        if vlan:
            vlans.append(vlan)

        self.vlans = vlans

        self.ip = kwargs.pop('ip', None)
        self.netmask = kwargs.pop('netmask', None)
        self.gateway = kwargs.pop('gateway', None)

        self.dhcp = kwargs.pop('dhcp', False)
        self.nat = kwargs.pop('nat', False)

        self._bb_port = None

    @property
    def bbport(self):
        # type: () -> byteblower.ByteBlowerPort
        return self._bb_port

    @bbport.setter
    def bbport(self, value):
        self._bb_port = value

    def create_on_server(self, server):
        logging.info("Creating a port on interface %s" % self.interface)
        self._bb_port = server.PortCreate(self.interface)
        self.bbport.Layer2EthIISet().MacSet(self.mac)

        for vlan_id in self.vlans:
            l2_5 = self.bbport.Layer25VlanAdd()
            l2_5.IDSet(vlan_id)

        l3 = self.bbport.Layer3IPv4Set()
        if self.dhcp:
            dhcp = l3.ProtocolDhcpGet()
            dhcp.Perform()
            self.ip = l3.IpGet()
            self.gateway = l3.GatewayGet()
            self.netmask = l3.NetmaskGet()
        else:
            l3.IpSet(self.ip)
            l3.NetmaskSet(self.netmask)
            l3.GatewaySet(self.gateway)

        logging.info('Created port: %s' % self.bbport.DescriptionGet())


class NATResolver:
    @classmethod
    def resolve(cls, wan_device, private_device, udp_src_port, udp_dst_port):

        from scapy.layers.inet import UDP, IP, Ether
        from scapy.all import Dot1Q

        wan_port = wan_device.bbport
        wan_ip = wan_port.Layer3IPv4Get().IpGet()

        private_port = private_device.bbport
        private_ip = private_port.Layer3IPv4Get().IpGet()
        private_mac = private_port.Layer2EthIIGet().MacGet()

        cap = None
        stream = None
        try:
            resolved_mac = private_port.Layer3IPv4Get().Resolve(wan_ip)

            stream = private_port.TxStreamAdd()
            bb_frame = stream.FrameAdd()
            scapy_frame = Ether(src=private_mac, dst=resolved_mac)
            for vlan_id in private_device.vlans:
                scapy_frame /= Dot1Q(vlan=vlan_id)

            scapy_frame /= IP(src=private_ip, dst=wan_ip)
            scapy_frame /= UDP(dport=udp_dst_port, sport=udp_src_port)
            scapy_frame /= 'Excentis NAT Discovery packet'

            frame_content = bytearray(bytes(scapy_frame))
            hexbytes = ''.join((format(b, "02x") for b in frame_content))

            # Send a single Probing frame.
            bb_frame.BytesSet(hexbytes)
            stream.NumberOfFramesSet(10)
            stream.InterFrameGapSet(1000 * 1000)  # 1 millisecond in nanos.

            cap = wan_port.RxCaptureBasicAdd()
            filter_elements = []
            for vlan in wan_device.vlans:
                filter_elements.append("vlan %d" % vlan)

            # normal filter:
            filter_elements.append("ip dst %s" % wan_ip)
            filter_elements.append("udp port %d" % udp_dst_port)
            bpf_filter = ' and '.join(filter_elements)
            cap.FilterSet(bpf_filter)
            cap.Start()

            stream.Start()

            # Stop as soon as you receive any response.
            while True:
                sniffed = cap.ResultGet()
                sniffed.Refresh()

                if sniffed.PacketCountGet() > 2:
                    break

                time.sleep(0.1)

            # The Capture needs to stopped explicitly.
            cap.Stop()

            # Process the response: retrieve all packets.
            for f in sniffed.FramesGet():
                data = bytearray(f.BufferGet())
                raw = Ether(data)
                if IP in raw and UDP in raw:
                    discovered_ip = raw['IP'].getfieldval('src')
                    discovered_udp_port = raw['UDP'].getfieldval('sport')
                    return discovered_ip, discovered_udp_port
            raise RuntimeError("NAT detection frames didn't get through")
        finally:
            if stream is not None:
                private_port.TxStreamRemove(stream)

            if cap is not None:
                wan_port.RxCaptureBasicRemove(cap)


class UdpTrafficProfile(object):
    """A Frame Blasting Traffic Profile

    This profile is a bit comparable to the the FrameBlasting Template in the
    ByteBlower GUI.  It currently has 2 configurable parameters:
    - The frame size to be sent
    - The frame interval (aka inter frame gap)

    """

    def __init__(self, **kwargs):
        self.interframegap_ns = kwargs.pop('interframegap', 1000000)
        self.frame_size = kwargs.pop('frame_size', 1020)

    def create_between(self, name, flow_number, source, destination, number_of_frames=None, duration=None):
        """Create a flow for the current traffic profile

        :type name: str
        :type flow_number: int
        :type source: Device
        :type destination: Device
        :type number_of_frames: int
        :type duration: datetime.timedelta
        :rtype: UdpFlow
        """
        if number_of_frames is None:
            duration_s = duration.total_seconds()
            number_of_frames = int(math.ceil(duration_s * 1e9 / self.interframegap_ns))

        udp_src = 4096 + flow_number
        udp_dest = 4096 + flow_number

        # Collect the basic addressing info for the Tx side.
        # VLAN id handled lower in the code.
        src_ip = source.ip
        src_mac = source.bbport.Layer2EthIIGet().MacGet()

        dst_ip = destination.ip

        logging.info("Resolving destination MAC for %s", dst_ip)
        dst_mac = source.bbport.Layer3IPv4Get().Resolve(dst_ip)

        frame_dst_ip = destination.ip
        frame_dst_port = udp_dest
        filter_dst_ip = destination.ip
        filter_dst_port = udp_dest

        if source.nat and destination.nat:
            raise RuntimeError("Cannot resolve traffic between multiple NAT ports")

        if source.nat:
            # no need to resolve here, since we only trigger on
            # destination parameters
            pass

        if destination.nat:
            logging.info("Resolving NAT parameters")
            # destination port is behind a NAT, probably need to 'poke' a hole
            frame_dst_ip, frame_dst_port = NATResolver.resolve(
                wan_device=source, private_device=destination,
                udp_src_port=udp_dest, udp_dst_port=udp_dest
            )

            logging.info("Resolving destination MAC for %s", frame_dst_ip)
            dst_mac = source.bbport.Layer3IPv4Get().Resolve(dst_ip)

        stream = source.bbport.TxStreamAdd()
        stream.NumberOfFramesSet(number_of_frames)
        stream.InterFrameGapSet(self.interframegap_ns)

        frame = stream.FrameAdd()

        payload = 'a' * (self.frame_size - 42)

        from scapy.layers.inet import UDP, IP, Ether
        from scapy.all import Raw, Dot1Q

        # A stream will always send the packet just as configured.
        # When the Tx ByteBlower port has a VLAN, we need to add it
        # to frame to be sent.
        # The following 5 lines are the only difference compared
        # to the basic IPv4 example.
        scapy_frame = Ether(src=src_mac, dst=dst_mac)

        for vlan_id in source.vlans:
            scapy_frame /= Dot1Q(vlan=vlan_id)

        scapy_frame /= IP(src=src_ip, dst=frame_dst_ip)
        scapy_frame /= UDP(dport=frame_dst_port, sport=udp_src)
        scapy_frame /= Raw(payload.encode('ascii', 'strict'))

        logging.debug('Created frame %s', repr(scapy_frame))

        frame_content = bytearray(bytes(scapy_frame))
        hexbytes = ''.join((format(b, "02x") for b in frame_content))
        frame.BytesSet(hexbytes)

        # create a trigger to count the number of received frames.
        # Similar to the stream we will need to make a slight modification
        # for the Vlan layer.
        trigger = destination.bbport.RxTriggerBasicAdd()

        # The BPF filter on a trigger is promiscous: it will be applied to all
        # traffic that arrives at the Physical interface.
        #
        # When we expect to receive packets with a VLAN, we need to add
        # this element to the filter.
        filter_elements = []
        for vlan in destination.vlans:
            filter_elements.append("vlan %d" % vlan)

        # normal filter:
        filter_elements.append("ip dst %s" % filter_dst_ip)
        filter_elements.append("udp port %d" % filter_dst_port)
        bpf_filter = ' and '.join(filter_elements)
        trigger.FilterSet(bpf_filter)

        return UdpFlow(name, stream, trigger)


class UdpFlow(object):
    """Frame blasting UDP Flow.


    """

    def __init__(self, name, stream, trigger):
        self.name = name
        self.stream = stream
        self.trigger = trigger

    def get_duration(self):
        """Calculates the actual duration of the UDP flow"""
        duration_ns = self.stream.InitialTimeToWaitGet()
        duration_ns += self.stream.NumberOfFramesGet() * self.stream.InterFrameGapGet()
        return datetime.timedelta(seconds=duration_ns / 1e9)

    def get_results_to_refresh(self):
        """Returns a list of interesting results we want to keep track of

        :rtype: [Union[TxStreamResult, TxStreamResultHistory, RxTriggerBasicResult, RxTriggerBasicResultHistory]]
        """
        return [
            self.stream.ResultGet(), self.stream.ResultHistoryGet(),
            self.trigger.ResultGet(), self.trigger.ResultHistoryGet()
        ]

    def reset_results(self):
        """Resets all results to an empty set"""
        self.stream.ResultClear()
        self.trigger.ResultClear()

    def process_interval_results(self):
        # ideal place to collect our results over time, but for now we'll
        # only log the last result in the snapshots

        stream_history = self.stream.ResultHistoryGet()
        stream_interval = stream_history.IntervalLatestGet()
        trigger_history = self.trigger.ResultHistoryGet()
        trigger_interval = trigger_history.IntervalLatestGet()

        logging.info('Flow %s: sent %d, received %d',
                     self.name,
                     stream_interval.PacketCountGet(),
                     trigger_interval.PacketCountGet()
                     )

    def get_results(self):
        stream_result = self.stream.ResultGet()
        stream_history = self.stream.ResultHistoryGet()
        trigger_result = self.trigger.ResultGet()
        trigger_history = self.trigger.ResultHistoryGet()

        frames_lost = stream_result.PacketCountGet() - trigger_result.PacketCountGet()

        procent_lost = 100.0 * frames_lost / stream_result.PacketCountGet()

        return {
            'name': self.name,
            'tx': {
                'total_bytes': stream_result.ByteCountGet(),
                'total_frames': stream_result.PacketCountGet(),
                'intervals': [
                    {
                        'timestamp': interval.TimestampGet(),
                        'bytes': interval.ByteCountGet(),
                        'frames': interval.PacketCountGet()
                    } for interval in stream_history.IntervalGet()
                ],
            },
            'rx': {
                'total_bytes': trigger_result.ByteCountGet(),
                'total_frames': trigger_result.PacketCountGet(),
                'intervals': [
                    {
                        'timestamp': interval.TimestampGet(),
                        'bytes': interval.ByteCountGet(),
                        'frames': interval.PacketCountGet()
                    } for interval in trigger_history.IntervalGet()
                ],
            },
            'total_frames_lost': frames_lost,
            'total_pct_lost': procent_lost

        }


class Example(object):
    def __init__(self, **kwargs):
        self.server_address = kwargs.pop('server_address')
        self.wan_port = kwargs.pop('wan_port')
        self.cpe_port = kwargs.pop('cpe_port')
        self.traffic_profile = kwargs.pop('traffic_profile')
        self.number_of_downstream_flows = kwargs.pop('number_of_downstream_flows', 2)
        self.number_of_upstream_flows = kwargs.pop('number_of_upstream_flows', 2)
        self.traffic_duration = kwargs.pop('traffic_duration', datetime.timedelta(seconds=10))

        self._server = None

    @property
    def server(self):
        # type: () -> byteblower.ByteBlowerServer
        return self._server

    def __enter__(self):
        instance = byteblower.ByteBlower.InstanceGet()
        logging.info('Connecting to server %s' % self.server_address)
        self._server = instance.ServerAdd(self.server_address)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()

    def resolve_nat(self):
        pass

    def run_traffic(self, flows, extra_duration=None):
        # type: ([UdpFlow], datetime.timedelta) -> None
        """Short helper function which actually runs the traffic

        It starts the ByteBlowerPorts and makes sure all the results of
        interest are refreshed
        """

        if extra_duration is None:
            extra_duration = datetime.timedelta(seconds=2)

        duration = max([flow.get_duration() for flow in flows])

        ports_to_start = byteblower.ByteBlowerPortList()
        ports_to_start.push_back(self.wan_port.bbport)
        ports_to_start.push_back(self.cpe_port.bbport)
        logging.info('Starting traffic for %s', duration)
        self.server.PortsStart(ports_to_start)

        duration += extra_duration
        stoptime = datetime.datetime.now() + duration

        while datetime.datetime.now() < stoptime:
            self.server.ResultsRefreshAll()
            time.sleep(.5)
            for flow in flows:
                flow.process_interval_results()

        logging.info('Traffic should be done')

    def cleanup(self):
        for device in [self.cpe_port, self.wan_port]:
            if device.bbport:
                self.server.PortDestroy(device.bbport)
            device.bbport = None

        instance = byteblower.ByteBlower.InstanceGet()
        instance.ServerRemove(self.server)
        self._server = None

    def run(self):
        """Main function of the example.  It executes it.
        """

        # Create the ports
        self.wan_port.create_on_server(self.server)
        self.cpe_port.create_on_server(self.server)

        flows = []

        # Create all the downstream flows which are requested
        for i in range(self.number_of_downstream_flows):
            flow_name = "Downstream_%d" % (i + 1)
            logging.info('Creating flow "%s"', flow_name)
            flows.append(
                self.traffic_profile.create_between(name=flow_name,
                                                    flow_number=i + 1,
                                                    source=self.wan_port,
                                                    destination=self.cpe_port,
                                                    duration=self.traffic_duration)
            )

        # Create all the upstream flows which are configured
        for i in range(self.number_of_upstream_flows):
            flow_name = "Upstream_%d" % (i + 1)
            logging.info('Creating flow "%s"', flow_name)
            flows.append(
                self.traffic_profile.create_between(name=flow_name,
                                                    flow_number=i + 1,
                                                    source=self.cpe_port,
                                                    destination=self.wan_port,
                                                    duration=self.traffic_duration)
            )

        # Start the traffic and with until finished
        self.run_traffic(flows)

        # Get the results from the flow and return them in a list of dicts
        return [flow.get_results() for flow in flows]


def run_example_vlan_nat():
    """Configures an example with the following parameters
    - The WAN port is on nontrunk-1.  It needs a VLAN (2) to reach its gateways
    - The CPE port is located on trunk-1-25, it needs NAT resolving to receive
      traffic from the WAN port

    - Traffic to be sent will be UDP traffic of 508 bytes (+ 4 bytes CRC) and
      will be sent at 1000 packets/s (frame interval is 1ms)
    - There will be 2 traffic flows from the WAN port to the CPE port
    - There will be 1 traffic flow from the CPE port to the WAN port
    - Traffic will be sent for 3 seconds
    """
    config = {
        'server_address': 'byteblower-tp-1300.lab.byteblower.excentis.com',
        'wan_port': Device(interface='nontrunk-1',
                           mac='00:ff:1f:00:00:01', vlan=2,
                           ip='172.24.0.2', netmask='255.252.0.0', gateway='172.24.0.1'),
        'cpe_port': Device(interface='trunk-1-25', dhcp=True, nat=True),
        'traffic_profile': UdpTrafficProfile(interframegap=1000000,  # ns
                                             frame_size=508  # bytes
                                             ),
        'number_of_downstream_flows': 2,
        'number_of_upstream_flows': 1,
        'traffic_duration': datetime.timedelta(seconds=3)
    }

    with Example(**config) as example:
        results = example.run()
        return results


def run_example_no_vlan_no_nat():
    """Configures an example with the following parameters
    - The WAN port is on nontrunk-1.  It provisions using DHCP
    - The CPE port is located on trunk-1-13, it provisions DHCP and it just in
      a routable subnet and doesn't need NAT
    - Traffic to be sent will be UDP traffic of 508 bytes (+ 4 bytes CRC) and
      will be sent at 1000 packets/s (frame interval is 1ms)
    - There will be 2 traffic flows from the WAN port to the CPE port
    - There will be 1 traffic flow from the CPE port to the WAN port
    - Traffic will be sent for 3 seconds
    """
    config = {
        'server_address': 'byteblower-tp-1300.lab.byteblower.excentis.com',
        'wan_port': Device(interface='nontrunk-1',
                           mac='00:ff:1f:00:00:01',
                           dhcp=True),
        'cpe_port': Device(interface='trunk-1-13', dhcp=True),
        'traffic_profile': UdpTrafficProfile(interframegap=1000000,  # ns
                                             frame_size=508  # bytes
                                             ),
        'number_of_downstream_flows': 2,
        'number_of_upstream_flows': 1,
        'traffic_duration': datetime.timedelta(seconds=3)
    }

    with Example(**config) as example:
        results = example.run()
        return results


if __name__ == '__main__':
    import sys
    import pprint

    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    result = run_example_vlan_nat()
    pprint.pprint(result)
