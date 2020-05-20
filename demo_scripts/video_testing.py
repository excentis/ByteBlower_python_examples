""""Wireless-Endpoint Video testing demo

This example demonstrates how to configure a Wireless Endpoint and the
ByteBlower server to run a Basic Video Test.

The Video Profile is based on some research we have done and is for now hard-
coded in the Wireless Endpoint.  In a later stage, this video profile might be
configurable.

The Profile has the following parameters:

- Maximum Video Buffer Size: 20 Megabytes (20000000 bytes)
- Video segment size: 2 Megabytes.
- Minimum Video Buffer Size: 2 Megabytes
- Video bitrate: 8 Mbps

The VideoPlayer will stop 'consuming' data from the buffer when the Buffer Size
drops below the minimum Video Buffer Size parameter.  When this happens, a user
will notice a hick-up during playback.
Whenever there is room in the video buffer, the Wireless Endpoint will download
a segment.

This example only processes a few results from the Wireless Endpoint, there are
more available and probably more will be added in a later release.  Here's a
list of items available at this stage:

- Downloader.Bytes: Number of Bytes downloaded in this interval
- Downloader.Segments: Number of Video Segments downloaded.
- Player.Buffer: Size of the Video Buffer.
- Player.BufferingTime: Time the VideoPlayer was waiting for the buffer to fill
- Player.BufferingTime.Initial: Time it took for the VideoPlayer to start.
- Player.Bytes: Number of bytes consumed from the VideoBuffer
- Player.Pauses: Number of times the video has stalled after playback started.

"""
from __future__ import print_function

import datetime
import random
import sys
import time

from byteblowerll.byteblower import ByteBlower, DeviceStatus_Reserved

configuration = {
    # Address (IP or FQDN) of the ByteBlower server to use
    'server_address': '10.10.1.204',

    # Interface on the server to create a port on.
    'server_interface': 'trunk-1-2',

    # MAC address of the ByteBlower port which will be generated
    'port_mac_address': '00:bb:01:00:00:01',

    # DHCP or IP configuration for the ByteBlower port
    # if DHCP, use "dhcp"
    'port_ip_address': 'dhcp',
    # if static, use ["ipaddress", "netmask", "gateway"]
    # 'port_ip_address': ['172.16.0.4', '255.255.252.0', '172.16.0.1'],

    # Address (IP or FQDN) of the ByteBlower Meetingpoint to use.  The wireless
    # endpoint *must* be registered on this meetingpoint.
    # Special value: None.  When the address is set to None, the server_address
    #                       will be used.
    # 'meetingpoint_address': '10.10.1.204',

    # UUID of the ByteBlower WirelessEndpoint to use.  This wireless endpoint
    # *must* be registered to the meetingpoint  configured by
    # meetingpoint_address.
    # When the UUID entry is omitted or set to None, the example will
    # automatically select the first available wireless endpoint.
    # 'wireless_endpoint_uuid': '37cea3f2-79a8-4fc3-8f6d-2736fcce3313',

    # TCP port for the VideoServer
    'port_tcp_port': 4096,

    # duration, in nanoseconds
    # Duration of the session
    #           sec  milli  micro  nano
    'duration': 180 * 1000 * 1000 * 1000,

    # TOS value to use on the HTTP client (and server)
    'tos': 0
}


class Example:
    def __init__(self, **kwargs):
        self.server_address = kwargs.pop('server_address')
        self.server_interface = kwargs.pop('server_interface')
        self.port_mac_address = kwargs.pop('port_mac_address')
        self.port_ip_address = kwargs.pop('port_ip_address')

        self.meetingpoint_address = kwargs.pop('meetingpoint_address', self.server_address)
        if self.meetingpoint_address is None:
            self.meetingpoint_address = self.server_address

        self.wireless_endpoint_uuid = kwargs.pop('wireless_endpoint_uuid', None)

        self.port_tcp_port = kwargs.pop('port_tcp_port', random.randint(10000, 40000))

        self.duration = kwargs.pop('duration')

        # Number of samples per second
        self.sample_resolution = 1
        # duration of the samples taken. (nanoseconds)
        self.sample_duration = int(1000000000 / self.sample_resolution)

        # number of samples to take:
        # ( test_duration / sample_duration) is just enough, so we are doubling
        # this so we have more than enough
        self.sample_count = int(2 * (self.duration / self.sample_duration))

        self.server = None
        self.port = None
        self.meetingpoint = None
        self.wireless_endpoint = None

    def __enter__(self):
        instance = ByteBlower.InstanceGet()

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

        # Claim the wireless endpoint for ourselves.  This means that nobody
        # but us can use this device.
        self.wireless_endpoint.Lock(True)

        return self

    def __exit__(self, *args, **kwargs):
        instance = ByteBlower.InstanceGet()

        if self.wireless_endpoint is not None:
            self.wireless_endpoint.Lock(False)

        if self.meetingpoint is not None:
            instance.MeetingPointRemove(self.meetingpoint)
            self.meetingpoint = None

        if self.port is not None:
            self.server.PortDestroy(self.port)
            self.port = None

        if self.server is not None:
            instance.ServerRemove(self.server)
            self.server = None

    def _run_scenario(self):
        # Send the scenario to the wireless endpoint
        self.wireless_endpoint.Prepare()

        # Start the wireless endpoint.
        # Actually, the function will return earlier, since the MeetingPoint
        # schedules the start some time in the future, to make sure all
        # devices start at the same time.
        self.wireless_endpoint.Start()

        # Wait until the device returns.
        # As long the device is running, the device will be in
        # - DeviceStatus_Starting
        # - DeviceStatus_Running
        # As soon the device has finished the test, it will return to
        # 'DeviceStatus_Reserved', since we have a Lock on the device.
        status = self.wireless_endpoint.StatusGet()
        start_moment = datetime.datetime.now()
        while status != DeviceStatus_Reserved:
            time.sleep(1)
            status = self.wireless_endpoint.StatusGet()
            now = datetime.datetime.now()
            print(str(now), ":: Running for", str(now - start_moment))

        # Wireless Endpoint has returned. Collect and process the results.

        # Fetch the results from the wireless endpoint, they will be stored
        # at the MeetingPoint, we will fetch the results in a following step.
        self.wireless_endpoint.ResultGet()

    def _create_video_server(self):
        """This will create a Video server

        The VideoServer is actually a ByteBlower HTTP Server which doesn't have
        sessions.  The WirelessEndpoint will connect to this server.
        """

        # Configure the HTTP server, running on the ByteBlower port.
        http_server = self.port.ProtocolHttpMultiServerAdd()

        # If the TCP port on which the the Video server needs to listen is not
        # given, select one randomly.
        if self.port_tcp_port is None:
            self.port_tcp_port = random.randint(10000, 40000)

        # Configure the TCP port on which the HTTP server wll listen
        http_server.PortSet(self.port_tcp_port)

        # A HTTP server will not listen for new connections as long it is not
        # started.  You can compare it to e.g. Apache or nginx, it won't accept
        # new connections as long the daemon is not started.
        http_server.Start()

        return http_server

    def _create_video_client(self):
        # Configure the client.

        # Hence the X in the name.  The X stands for "Experimental".  As soon
        # the feature will be offically released, the "X" will vanish.
        video_client = self.wireless_endpoint.XVideoClientAdd()
        # Configure the remote endpoint to which it must connect.
        # This is the IP address and port of the HTTP server configured above
        video_client.RemoteAddressSet(self.port.Layer3IPv4Get().IpGet())
        video_client.RemotePortSet(self.port_tcp_port)

        video_client.DurationSet(self.duration)

        # Not supported YET
        # video_client.RequestInitialTimeToWaitSet(0)

        # Not support YET
        # video_client.TypeOfServiceSet(self.tos)
        return video_client

    def run(self):

        # Configure the HTTP server, running on the ByteBlower port.
        video_server = self._create_video_server()
        print("HTTP server configuration:", video_server.DescriptionGet())

        # Configure the client.
        video_client = self._create_video_client()
        print("Video client configuration:", video_client.DescriptionGet())

        # Run the configured scenario
        self._run_scenario()

        # Collect the results
        results = []

        snapshot = video_client.ResultGet()
        print("Video test summary:")
        print(snapshot.DescriptionGet())

        history = video_client.ResultHistoryGet()
        intervals = history.IntervalGet()
        for interval in intervals:
            results.append({
                'timestamp': interval.TimestampGet(),
                'buffer_size': interval.PlayerBufferSizeGet().BytesGet(),
                'bytes_downloaded': interval.DownloaderBytesGet().BytesGet(),
                'player_buffered_bytes_consumed': interval.PlayerBytesPlayedGet().BytesGet()
            })

        return results

    def select_wireless_endpoint_uuid(self):
        """
        Walk over all known devices on the meetingpoint.
        If the device has the status 'Available', return its UUID, otherwise
        return None.

        :return: a string representing the UUID or None
        :rtype: str
        """
        from byteblowerll.byteblower import DeviceStatus_Available

        for device in self.meetingpoint.DeviceListGet():
            # is the status Available?
            if device.StatusGet() == DeviceStatus_Available:
                # yes, return the UUID
                return device.DeviceIdentifierGet()

        # No device found, return None
        return None


if __name__ == '__main__':
    with Example(**configuration) as example:
        # Collect some information
        selected_device_name = example.wireless_endpoint.DeviceInfoGet().GivenNameGet()
        example_results = example.run()

        from plotting import video
        video.plot_data(selected_device_name, example_results, "video_testing.html")

    sys.exit(0)
