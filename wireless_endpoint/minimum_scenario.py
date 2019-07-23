#!/usr/bin/python
""""
This example allows the user to configure a frameblasting flow which transmits data to the wireless endpoint.

WirelessEndpoint --> ByteBlowerPort
"""

from __future__ import print_function
import time
# We want to use the ByteBlower python API, so import it
from byteblowerll.byteblower import ByteBlower

# We will use scapy to build the frames, scapy will be imported when needed.


configuration = {
    # Address (IP or FQDN) of the ByteBlower server to use
    'server_address': 'byteblower-tutorial-1300.lab.byteblower.excentis.com',

    # Interface on the server to create a port on.
    'server_interface': 'nontrunk-1',

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
    # 'wireless_endpoint_uuid': None,
    'wireless_endpoint_uuid': '65e298b8-5206-455c-8a38-6cd254fc59a2',

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

        # Connect to the meetingpoint
        self.meetingpoint = instance.MeetingPointAdd(self.meetingpoint_address)

        # If no WirelessEndpoint UUID was given, search an available one.
        if self.wireless_endpoint_uuid is None:
            self.wireless_endpoint_uuid = self.select_wireless_endpoint_uuid()

        # Get the WirelessEndpoint device
        self.wireless_endpoint = self.meetingpoint.DeviceGet(self.wireless_endpoint_uuid)
        print("Using wireless endpoint", self.wireless_endpoint.DeviceInfoGet().GivenNameGet())

        durationScenario = 5000000000
        self.wireless_endpoint.ScenarioDurationSet(durationScenario)


        # Make sure we are the only users for the wireless endpoint
        self.wireless_endpoint.Lock(True)

        # Upload the configuration to the wireless endpoint
        self.wireless_endpoint.Prepare()

        from time import sleep

        #starting the wireless endpoint
        starttime_posix = self.wireless_endpoint.Start()
        # Current POSIX timestamp on the meetingpoint
        current_time_posix = self.meetingpoint.TimestampGet()

        time_to_wait_ns = starttime_posix - current_time_posix
        # Wait 200 ms longer, to make sure the wireless endpoint has started.
        time_to_wait_ns += 200000000

        print("Waiting for", time_to_wait_ns / 1000000000.0, "to start the wireless endpoint")
        sleep(time_to_wait_ns / 1000000000.0)

        print("wireless endpoint will be running for", durationScenario / 1000000000.0, "seconds")

        print("Waiting for the test to finish")
        sleep(durationScenario / 1000000000.0)

        self.wireless_endpoint.Lock(False)
        instance.MeetingPointRemove(self.meetingpoint)

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


if __name__ == '__main__':
    Example(**configuration).run()
