#!/usr/bin/python
""""
This example configures an empty scenario on a Wireless Endpoint.
This causes the device to be silent and thus not disrupting other tests.

"""

from __future__ import print_function

# We want to use the ByteBlower python API, so import it
from byteblowerll.byteblower import ByteBlower

# We will use scapy to build the frames, scapy will be imported when needed.


configuration = {
    # Address (IP or FQDN) of the ByteBlower Meetingpoint to use.  The wireless endpoint *must* be registered
    # on this meetingpoint.
    'meetingpoint_address': 'byteblower-tutorial-1300.lab.byteblower.excentis.com',

    # UUID of the ByteBlower WirelessEndpoint to use.  This wireless endpoint *must* be registered to the meetingpoint
    # configured by meetingpoint_address.
    # Special value: None.  When the UUID is set to None, the example will automatically select the first available
    # wireless endpoint.
    # 'wireless_endpoint_uuid': None,
    'wireless_endpoint_uuid': '65e298b8-5206-455c-8a38-6cd254fc59a2',
}


class Example:
    def __init__(self, **kwargs):
        self.meetingpoint_address = kwargs['meetingpoint_address']

        self.wireless_endpoint_uuid = kwargs['wireless_endpoint_uuid']

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

        duration_scenario = 5000000000
        self.wireless_endpoint.ScenarioDurationSet(duration_scenario)

        # Make sure we are the only users for the wireless endpoint
        self.wireless_endpoint.Lock(True)

        # Upload the configuration to the wireless endpoint
        self.wireless_endpoint.Prepare()

        from time import sleep

        # starting the wireless endpoint
        starttime_posix = self.wireless_endpoint.Start()
        # Current POSIX timestamp on the meetingpoint
        current_time_posix = self.meetingpoint.TimestampGet()

        time_to_wait_ns = starttime_posix - current_time_posix
        # Wait 200 ms longer, to make sure the wireless endpoint has started.
        time_to_wait_ns += 200000000

        print("Waiting for", time_to_wait_ns / 1000000000.0, "to start the wireless endpoint")
        sleep(time_to_wait_ns / 1000000000.0)

        print("wireless endpoint will be running for", duration_scenario / 1000000000.0, "seconds")

        print("Waiting for the test to finish")
        sleep(duration_scenario / 1000000000.0)

        self.wireless_endpoint.Lock(False)

    def cleanup(self):
        instance = ByteBlower.InstanceGet()
        if self.meetingpoint is not None:
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
    example = Example(**configuration)
    try:
        example.run()
    finally:
        example.cleanup()
