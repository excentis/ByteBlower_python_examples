"""
This example shows how to perform QED (Quality of Experience Delivered) measurements with the ByteBlower Python API.
The script creates network traffic that simulates Counterstrike gaming traffic.
A ByteBlower port is used to simulate the game server.
A ByteBlower Endpoint is used to simulate gaming on a laptop.
The gaming traffic consists of a downstream and upstream traffic:
 * Downstream traffic: 128 UDP packets per second, with an average size of 500 bytes per packet
 * Upstream traffic: 128 UDP packets per second, with an average size of 200 bytes per packet
To verify the QED, you can specify the qed_percentiles.
Each item consist of a percentile and a corresponding latency in nanoseconds.
For example:
    'qed_percentiles': { 75: 90000000, 90: 250000000, 99: 300000000 }
This means that
 * you want 75% of the traffic to have a latency below 90ms.
 * you want 90% of the traffic to have a latency below 250ms.
 * you want 99% of the traffic to have a latency below 300ms.
The example returns measured QED over time.
These results can be used by a testing tool like pytest.
This way you can write automated tests to guarantee Quality of Experience.

All examples are guaranteed to work with Python 2.7 and above

Copyright 2023, Excentis N.V.
"""


from __future__ import division
from __future__ import print_function

import collections
import json
import math
import time
from datetime import datetime

from byteblowerll import byteblower as api
from highcharts import Highchart

configuration = {
    # Address (IP or FQDN) of the ByteBlower server to use
    'server_address': '10.10.1.202',

    # Interface on the server to create a port on.
    'server_interface': 'trunk-1-7',

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
    # 'wireless_endpoint_uuid': None,
    # 'wireless_endpoint_uuid': '977d5a57-8668-436e-ae81-2cfda87cc8ef',  # laptop 56
    'wireless_endpoint_uuid': '3c2e5afe66779ec7',  # S10e
    # 'wireless_endpoint_uuid': '65e298b8-5206-455c-8a38-6cd254fc59a2',

    # Whether the Wireless Endpoint is behind a NATted device.
    # e.g. a home-router.  If unsure, leave on True
    'wireless_endpoint_nat': True,

    # Size of the frame on ethernet level. Do not include the CRC
    'ds_frame_size': 500,  # Average downstream packet size for Counter Strike gaming traffic
    'us_frame_size': 200,  # Average upstream packet size for Counter Strike gaming traffic

    # Number of frames to send.
    # 'number_of_frames': 4000,
    # 'number_of_frames': 20000,
    'number_of_frames': 76800,  # 10m
    # 'number_of_frames': 153600,  # 20m
    # 'number_of_frames': 460800,  # 1h

    # How fast must the frames be sent.
    # 'interframe_gap_nanoseconds': 15625000, #64 pps equals "Casual Gaming"
    'interframe_gap_nanoseconds': 7812500,  # 128 pps equals "Pro Gaming"

    'udp_srcport': 4096,
    'udp_dstport': 4096,

    # Latency histogram range in nanoseconds.
    # The ByteBlower default is: 0 to 1 seconds
    'range_min': 0,
    # 'range_max': int(1e7),  # 10ms
    # 'range_max': int(2e7),  # 20ms
    'range_max': int(1e8),  # 100ms
    # 'range_max': int(2e8),  # 200ms
    # 'range_max': int(5e8),  # 500ms
    # 'range_max': int(1e9), #1s

    'qed_percentiles': {
        1: 4000000,
        25: 5000000,
        50: 10000000,
        75: 90000000,
        90: 250000000,
        99: 300000000,
        100: 500000000
    }
}


def make_cumulative(histogram):
    buckets = histogram.get('interval_packet_count_buckets')
    below_min = histogram.get('interval_packet_count_below_min')
    total = histogram.get('interval_packet_count')

    if total:
        percentage_below_range = below_min / total * 100
        histogram['percentage_below_range'] = percentage_below_range
        cumulative_histogram = calculate_cumulative_percentages(
            below_min,
            buckets,
            total)
        histogram['cumulative_buckets'] = cumulative_histogram


class Example:
    def __init__(self, **kwargs):
        self.server_address = kwargs.pop('server_address')
        self.server_interface = kwargs.pop('server_interface')
        self.port_mac_address = kwargs.pop('port_mac_address')
        self.port_ip_address = kwargs.pop('port_ip_address')

        self.meetingpoint_address = kwargs.pop('meetingpoint_address', None)
        if self.meetingpoint_address is None:
            self.meetingpoint_address = self.server_address

        self.wireless_endpoint_uuid = kwargs.pop('wireless_endpoint_uuid', None)
        self.wireless_endpoint_nat = kwargs.pop('wireless_endpoint_nat', True)

        self.ds_frame_size = kwargs.pop('ds_frame_size', 500)
        self.us_frame_size = kwargs.pop('us_frame_size', 200)
        self.number_of_frames = kwargs.pop('number_of_frames', 2000)
        self.frame_interval_nanoseconds = kwargs.pop('interframe_gap_nanoseconds', 10000000)
        self.expected_packets_per_second = 1e9 / self.frame_interval_nanoseconds

        self.udp_srcport = kwargs.pop('udp_srcport', 4096)
        self.udp_dstport = kwargs.pop('udp_dstport', 4096)

        self.range_min = kwargs.pop('range_min', 0)
        self.range_max = kwargs.pop('range_max', int(1e9))

        self.server = None
        self.port = None
        self.meetingpoint = None
        self.wireless_endpoint = None

        self.qed_percentiles = kwargs.pop('qed_percentiles')
        self.json_results_filename = 'samples.json'

        # Set to True when you want to save the test results and reuse them. This saves time while developing.
        self.reuse_results = False
        # self.reuse_results = True

        self.write_html_charts = True
        self.chart_title = 'Samsung S10e'
        # self.chart_title = 'Counterstrike - Laptop 56'

    def load_earlier_results(self):
        with open(self.json_results_filename) as json_file:
            return json.load(json_file)

    def get_buckets(self, histograms):
        buckets_history = []
        interval_length = histograms.IntervalLengthGet()

        for idx in range(interval_length):
            # interval: api.LatencyDistributionResultData = histograms.IntervalGetByIndex(idx)
            interval = histograms.IntervalGetByIndex(idx)
            interval_packet_count = interval.PacketCountGet()  # should be
            # interval_packet_loss = expected_packets_per_second - interval_packet_count
            bucket_count = interval.BucketCountGet()

            if interval_packet_count:
                packet_count_below_min = interval.PacketCountBelowMinimumGet()
                packet_count_buckets = [int(val) for val in interval.PacketCountBucketsGet()]
                packet_count_in_buckets = sum(packet_count_buckets)
                packet_count_above_max = interval.PacketCountAboveMaximumGet()
            else:
                packet_count_below_min = 0
                packet_count_buckets = [0 for _ in range(bucket_count)]
                packet_count_in_buckets = 0
                packet_count_above_max = 0

            buckets_history.append({
                'interval_timestamp': interval.TimestampGet(),
                'interval_range_min': interval.RangeMinimumGet(),
                'interval_range_max': interval.RangeMaximumGet(),
                'interval_packet_count': interval_packet_count,
                'interval_packet_count_below_min': packet_count_below_min,
                'interval_packet_count_in_buckets': packet_count_in_buckets,
                'interval_packet_count_buckets': packet_count_buckets,
                'interval_packet_count_above_max': packet_count_above_max
                # 'interval_packet_loss': interval_packet_loss
            })

        return buckets_history

    def run_new_test(self):
        byteblower_instance = api.ByteBlower.InstanceGet()

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

        cap = self.wireless_endpoint.CapabilityGetByName('Rx.Latency.Distribution')
        if not cap.ValueGet():
            print("Wireless Endpoint or MeetingPoint does not support latency Distribution Triggers")
            return

        # the destination MAC is the MAC address of the destination port if
        # the destination port is in the same subnet as the source port,
        # otherwise it will be the MAC address of the gateway.
        # ByteBlower has a function to resolve the correct MAC address in
        # the Layer3 configuration object
        network_info = self.wireless_endpoint.DeviceInfoGet().NetworkInfoGet()
        endpoint_ipv4 = network_info.IPv4Get()

        port_mac = self.port.Layer2EthIIGet().MacGet()
        port_layer3_config = self.port.Layer3IPv4Get()
        port_ipv4 = port_layer3_config.IpGet()

        destination_udp_port = self.udp_dstport
        if self.wireless_endpoint_nat:
            print("Resolving NAT")
            endpoint_ipv4, destination_udp_port = self.resolve_nat()
            print("Wireless Endpoint Public IP address %s" % endpoint_ipv4)

        # destination MAC must be resolved, since we do not know whether
        # the wireless endpoint is available on the local LAN
        ds_destination_mac = port_layer3_config.Resolve(endpoint_ipv4)

        ds_payload = 'd' * (self.ds_frame_size - 42)
        us_payload = 'u' * (self.us_frame_size - 42)

        duration_ns = self.frame_interval_nanoseconds * self.number_of_frames

        # Add 2 seconds of rollout, so frames in transit can be counted too
        duration_ns += 2 * 1000 * 1000 * 1000

        print("Creating the DS trigger...")
        # create a latency-enabled trigger.  A trigger is an object which
        # receives data.  The Basic trigger just count packets,
        # a LatencyBasic trigger analyzes the timestamps embedded in the
        # received frame.
        # ds_latency_trigger: api.LatencyDistributionMobile = self.wireless_endpoint.RxLatencyDistributionAdd()
        ds_latency_trigger = self.wireless_endpoint.RxLatencyDistributionAdd()
        ds_latency_trigger.DurationSet(duration_ns)
        ds_latency_trigger.FilterUdpSourcePortSet(self.udp_srcport)
        ds_latency_trigger.FilterUdpDestinationPortSet(self.udp_dstport)
        ds_latency_trigger.FilterSourceAddressSet(port_ipv4)
        ds_latency_trigger.RangeSet(self.range_min, self.range_max)

        print("Creating the US trigger...")
        # us_latency_trigger: api.LatencyDistribution = self.port.RxLatencyDistributionAdd()
        us_latency_trigger = self.port.RxLatencyDistributionAdd()
        bpf = "ip src host " + endpoint_ipv4 + " and udp src port " + str(self.udp_dstport)
        us_latency_trigger.FilterSet(bpf)
        us_latency_trigger.RangeSet(self.range_min, self.range_max)

        print("Creating the DOWN stream...")
        down_stream = self.port.TxStreamAdd()
        down_stream.InterFrameGapSet(self.frame_interval_nanoseconds)
        down_stream.NumberOfFramesSet(self.number_of_frames)

        print("Creating the UP stream...")
        # up_stream: api.StreamMobile = self.wireless_endpoint.TxStreamAdd()
        up_stream = self.wireless_endpoint.TxStreamAdd()
        up_stream.InterFrameGapSet(self.frame_interval_nanoseconds)
        up_stream.NumberOfFramesSet(self.number_of_frames)
        up_stream.DestinationAddressSet(port_ipv4)
        up_stream.DestinationPortSet(self.udp_srcport)
        up_stream.SourcePortSet(self.udp_dstport)

        from scapy.layers.inet import UDP, IP, Ether
        from scapy.all import Raw
        ds_udp_payload = Raw(ds_payload.encode('ascii', 'strict'))
        us_udp_payload = Raw(us_payload.encode('ascii', 'strict'))
        ds_udp_header = UDP(dport=destination_udp_port, sport=self.udp_srcport, chksum=0)
        ds_ip_header = IP(src=port_ipv4, dst=endpoint_ipv4)
        ds_eth_header = Ether(src=port_mac, dst=ds_destination_mac)
        ds_scapy_frame = ds_eth_header / ds_ip_header / ds_udp_header / ds_udp_payload
        ds_frame_content = bytearray(bytes(ds_scapy_frame))
        us_frame_content = bytearray(bytes(us_udp_payload))

        # The ByteBlower API expects an 'str' as input for the
        # frame.BytesSet() method, we need to convert the bytearray
        ds_hexbytes = ''.join((format(b, "02x") for b in ds_frame_content))
        us_hexbytes = ''.join((format(b, "02x") for b in us_frame_content))

        # Since a stream transmits frames, we need to tell the stream which
        # frames we want to transmit
        ds_frame = down_stream.FrameAdd()
        ds_frame.BytesSet(ds_hexbytes)

        # TODO - Add frame size modifier, to make the packet size vary according to a normal distribution
        # Add a random frame size modifier:
        # modifier: api.FrameSizeModifierRandom = ds_frame.ModifierSizeRandomSet()
        # modifier.MinimumSet(60)
        # modifier.MaximumSet(1283)

        # us_frame: api.FrameMobile = up_stream.FrameAdd()
        us_frame = up_stream.FrameAdd()
        us_frame.PayloadSet(us_hexbytes)

        # Enable latency for this frame.
        # The frame contents will be altered, so it contains a timestamp.
        ds_frame_tag = ds_frame.FrameTagTimeGet()
        ds_frame_tag.Enable(True)

        us_frame_tag = us_frame.FrameTagTimeGet()
        us_frame_tag.Enable(True)

        # Configure the scenario duration on the Wireless Endpoint.
        # Otherwise, it won't be able to determine how long the flow takes.
        duration_ns = self.frame_interval_nanoseconds * self.number_of_frames
        # wait an additional 2 second for buffered frames
        duration_ns += 2 * 1e9
        self.wireless_endpoint.ScenarioDurationSet(int(duration_ns))

        # Make sure we are the only users for the wireless endpoint
        self.wireless_endpoint.Lock(True)

        # Upload the configuration to the wireless endpoint
        print("Sending the scenario to the Wireless Endpoint")
        self.wireless_endpoint.Prepare()

        # print the configuration
        # This makes it easy to review what we have done until now
        print("Current ByteBlower configuration:")
        print("Down Stream:", down_stream.DescriptionGet())
        print("Up Stream:", up_stream.DescriptionGet())
        print("DS Trigger:", ds_latency_trigger.DescriptionGet())
        print("US Trigger:", us_latency_trigger.DescriptionGet())

        # start the traffic, clear the latency trigger.  Triggers are active
        # as soon they are created, so we may want to clear the data it already
        # has collected.
        print("Starting traffic")
        ds_latency_trigger.ResultClear()
        us_latency_trigger.ResultClear()

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

        down_stream.Start()

        # Getting the Histograms over time:
        # us_latency_result: api.LatencyDistributionResultSnapshot = us_latency_trigger.ResultGet()
        us_latency_result = us_latency_trigger.ResultGet()
        # us_history: api.LatencyDistributionResultHistory = us_latency_trigger.ResultHistoryGet()
        us_history = us_latency_trigger.ResultHistoryGet()

        print("Waiting for the test to finish")
        seconds = math.ceil(duration_ns / 1000000000.0)
        for second in range(seconds):
            sleep(1)
            # fetch US results regularly, because only 5 intervals max are stored on the server:
            us_history.Refresh()

        print("Done sending traffic")

        # Waiting for a second after the stream is finished.
        # This has the advantage that frames that were transmitted but were
        # not received yet, can be processed by the server
        print("Waiting for a second")
        sleep(1)

        # Get all results from the ByteBlower Endpoint
        self.wireless_endpoint.HeartbeatIntervalSet(10)
        self.wireless_endpoint.ResultGet()
        self.wireless_endpoint.HeartbeatIntervalSet(1)

        # ds_stream_result: api.StreamResultSnapshot = down_stream.ResultGet()
        ds_stream_result = down_stream.ResultGet()
        ds_stream_result.Refresh()

        # ds_latency_result: api.LatencyDistributionResultSnapshot = ds_latency_trigger.ResultGet()
        ds_latency_result = ds_latency_trigger.ResultGet()
        ds_latency_result.Refresh()

        print(ds_latency_result.DescriptionGet())

        # stream_result_history: api.LatencyDistributionResultHistory = down_stream.ResultHistoryGet()
        stream_result_history = down_stream.ResultHistoryGet()
        stream_result_history.Refresh()

        # Getting the Histograms over time:
        # ds_history: api.LatencyDistributionResultHistory = ds_latency_trigger.ResultHistoryGet()
        ds_history = ds_latency_trigger.ResultHistoryGet()
        ds_buckets_history = self.get_buckets(ds_history)

        us_latency_result.Refresh()
        us_buckets_history = self.get_buckets(us_history)
        print(us_latency_result.DescriptionGet())

        # Tell the ByteBlower server it can clean up its resources.
        self.server.PortDestroy(self.port)
        self.wireless_endpoint.Lock(False)

        output_dict = {
            'downstream': ds_buckets_history,
            'upstream': us_buckets_history
        }

        return output_dict

    def calculate_qed(self, histograms):
        qed_over_time = []

        for histogram in histograms:
            make_cumulative(histogram)

        for percent in self.qed_percentiles.keys():
            latencies = []
            for histogram in histograms:
                cumulative = histogram.get('cumulative_buckets')
                if cumulative:
                    below = histogram.get('interval_packet_count_below_min')

                    timestamp = datetime.fromtimestamp(histogram.get('interval_timestamp') // 1000000000)
                    interval_range_min = histogram.get('interval_range_min')
                    interval_range_max = histogram.get('interval_range_max')
                    percentage_below_range = histogram.get('percentage_below_range')
                    index = get_bucket_index(percentage_below_range, cumulative, percent)
                    rangetype = index.get('rangetype')
                    latency = None
                    if rangetype == RangeType.BELOW:
                        latency = None
                    elif rangetype == RangeType.INSIDE:
                        bucket_width = (interval_range_max - interval_range_min) / len(cumulative)
                        latency = interval_range_min + index.get('index') * bucket_width
                    elif rangetype == RangeType.ABOVE:
                        latency = None

                    latencies.append([timestamp, latency])

            qed_over_time.append({
                'percentile': percent,
                'latencies': latencies
            })
        return qed_over_time

    def run(self):
        results = None
        if self.reuse_results:
            results = self.load_earlier_results()

        if not results:
            results = self.run_new_test()
            with open(self.json_results_filename, "w") as outfile:
                json.dump(results, outfile)

        ds_qed = self.calculate_qed(results.get('downstream'))
        us_qed = self.calculate_qed(results.get('upstream'))

        if self.write_html_charts:
            write_html_chart(self.chart_title + ' - Downstream', ds_qed)
            write_html_chart(self.chart_title + ' - Upstream', us_qed)

        qed = {
            'downstream': ds_qed,
            'upstream': us_qed
        }

        return qed

    def cleanup(self):
        instance = api.ByteBlower.InstanceGet()

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
            if device.StatusGet() == api.DeviceStatus.Available:
                # yes, return the UUID
                return device.DeviceIdentifierGet()

        # No device found, return None
        return None

    def resolve_nat(self):
        stream = None
        cap = None
        try:
            from scapy.layers.inet import UDP, IP, Ether

            # Immediately start with capturing traffic.
            cap = self.port.RxCaptureBasicAdd()
            cap.FilterSet('ip and udp and udp port %d' % self.udp_srcport)
            cap.Start()

            # Next configure the probing traffic.
            # Create the requested packet.
            stream = self.wireless_endpoint.TxStreamAdd()
            bb_frame = stream.FrameAdd()
            bb_frame.PayloadSet('aa' * 60)

            # Send a single Probing frame.
            stream.NumberOfFramesSet(5)
            stream.InterFrameGapSet(1000 * 1000)  # 1 millisecond in nanos.

            stream.SourcePortSet(self.udp_dstport)
            stream.DestinationPortSet(self.udp_srcport)
            stream.DestinationAddressSet((self.port.Layer3IPv4Get().IpGet()))

            self.wireless_endpoint.Lock(True)
            self.wireless_endpoint.Prepare()

            start_time = self.wireless_endpoint.Start()
            current_time = self.meetingpoint.TimestampGet()

            time.sleep((start_time - current_time) / 1e9)

            for i in range(5):
                sniffed = cap.ResultGet()
                sniffed.Refresh()
                time.sleep(1)

            # The Capture needs to be stopped explicitly.
            cap.Stop()

            self.wait_for_device_available()
            self.wireless_endpoint.Lock(False)

            # Process the response: retrieve all packets.
            for f in cap.ResultGet().FramesGet():
                data = bytearray(f.BufferGet())
                raw = Ether(data)
                if IP in raw and UDP in raw:
                    discovered_ip = raw['IP'].getfieldval('src')
                    discovered_udp_port = raw['UDP'].getfieldval('sport')
                    print('Discovered IP: %s' % discovered_ip)
                    print('Discovered UDP port: %s' % discovered_udp_port)
                    return discovered_ip, discovered_udp_port
            else:
                print('No packet received')
        except api.ByteBlowerAPIException as e:
            print(e.what())
            raise
        finally:
            self.wireless_endpoint.Lock(False)
            if stream is not None:
                self.wireless_endpoint.TxStreamRemove(stream)

            if cap is not None:
                self.port.RxCaptureBasicRemove(cap)

    def wait_for_device_available(self):
        import datetime
        starttime = datetime.datetime.now()

        print("Waiting for the device to be back available")

        def is_done():
            if (datetime.datetime.now() - starttime) < datetime.timedelta(seconds=20):
                return True

            if self.wireless_endpoint.StatusGet() in [api.DeviceStatus.Available, api.DeviceStatus.Reserved]:
                return True

            return False

        while not is_done():
            time.sleep(1)

        print("Device back available")


def create_highcharts(title):
    chart = Highchart(width=1000, height=600)
    styling = '<span style="font-family: \'DejaVu Sans\', Arial, Helvetica, sans-serif; color: '
    options = {
        'title': {
            'text': styling +
                    '#00AEEF; font-size: 20px; line-height: 1.2640625; ">' + 'Pro Gaming ' + title + ' QED </span>'
        },
        'chart': {
            'zoomType': 'x'
        },
        'xAxis': {
            'type': 'datetime',
            'title': {
                'text': styling +
                        '#F7941C; font-size: 12px; line-height: 1.4640625; font-weight: bold;">Time [h:min:s]</span>'
            }
        },
        'yAxis': [
            {
                'title': {
                    'text': styling +
                            '#00AEEF; font-size: 12px; line-height: 1.2640625; font-weight: bold; ">Latency [ms]</span>'
                },
                'labels': {
                    'formatter': 'function(){return this.value/1e6}'
                }
            }
        ],
        'legend': {
            'title': {
                'text': styling +
                        '#F7941C; font-size: 12px; line-height: 1.4640625; font-weight: bold;">Percentiles</span>'
            }
        },
        'tooltip': {
            'formatter': 'function(){return this.y/1e6}'
        }
    }
    chart.set_dict_options(options)
    return chart


class RangeType():
    BELOW = 1
    INSIDE = 2
    ABOVE = 3


def get_bucket_index(percentage_below_range, cumulative_buckets, percent):
    if percent <= percentage_below_range:
        return {
            'rangetype': RangeType.BELOW,  # The corresponding latency is below the specified latency range
            'index': -1  # Dummy value
        }
    for idx, bucket in enumerate(cumulative_buckets):
        if percent <= bucket:
            return {
                'rangetype': RangeType.INSIDE,
                'index': idx
            }
    return {
        'rangetype': RangeType.ABOVE,  # The corresponding latency is above the specified latency range
        'index': -1  # Dummy value
    }


def calculate_cumulative_percentages(below, buckets, total):
    cumulative = []
    count = below
    for bucket in buckets:
        count += bucket
        cumulative.append(count / total * 100)
    return cumulative


def write_html_chart(title, qed):
    chart = create_highcharts(title)
    sorted_list = sorted(qed, key=lambda x: x['percentile'])
    for item in sorted_list:
        percentile = item.get('percentile')
        chart.add_data_set(item.get('latencies'), 'line', str(percentile), yAxis=0)
    chart.save_file(title)


if __name__ == "__main__":
    example = Example(**configuration)
    try:
        output = example.run()
    finally:
        example.cleanup()
