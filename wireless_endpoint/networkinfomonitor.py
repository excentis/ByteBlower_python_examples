#!/usr/bin/python
""""
This example allows the user to collect network information over time on a
Wireless Endpoint.

"""

from __future__ import print_function
import time
# We want to use the ByteBlower python API, so import it
from byteblowerll.byteblower import ByteBlower

# We will use scapy to build the frames, scapy will be imported when needed.


configuration = {

    # Address (IP or FQDN) of the ByteBlower Meetingpoint to use.  The wireless endpoint *must* be registered
    # on this meetingpoint.
    'meetingpoint_address': '10.10.1.202',

    # UUID of the ByteBlower WirelessEndpoint to use.  This wireless endpoint *must* be registered to the meetingpoint
    # configured by meetingpoint_address.
    # Special value: None.  When the UUID is set to None, the example will automatically select the first available
    # wireless endpoint.
    'wireless_endpoint_uuid': None,
    # 'wireless_endpoint_uuid': '86B6D1A7-72D0-4462-B8D0-ED5655F906CC',

    # Name of the Interface as given by the operating system.
    # 'wireless_interface': 'Intel(R) Dual Band Wireless-AC 8265',
    # 'wireless_interface': 'Intel(R) Wi-Fi 6 AX200 160MHz',
    # 'wireless_interface': 'wlan0',
    'wireless_interface': 'en0',

    # duration in seconds to poll for information
    # 'duration_s': 180,
    'duration_s': 20,
}


class Example:
    def __init__(self, **kwargs):

        self.meetingpoint_address = kwargs['meetingpoint_address']

        self.wireless_endpoint_uuid = kwargs['wireless_endpoint_uuid']
        self.wireless_interface = kwargs['wireless_interface']
        self.duration_s = kwargs['duration_s']

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

        # Make sure we are the only users for the wireless endpoint
        self.wireless_endpoint.Lock(True)

        device_info = self.wireless_endpoint.DeviceInfoGet()
        network_info_monitor = device_info.NetworkInfoMonitorAdd()
        self.wireless_endpoint.ScenarioDurationSet(self.duration_s * 1000000000)  # ns

        print("Starting the wireless endpoint")
        self.wireless_endpoint.Prepare()
        start_time = self.wireless_endpoint.Start()

        # Wait for the device to start
        print('Waiting for the wireless endpoint to start')
        current_time = self.meetingpoint.TimestampGet()
        time_to_sleep = (start_time - current_time) / 1000000000
        time.sleep(int(time_to_sleep))

        # Wait for the test to finish
        print('Waiting for the wireless endpoint to finish the test')
        time.sleep(self.duration_s)

        # Wait for the device to start beating again.
        # Default heartbeat interval is 1 seconds, so lets wait for 2 beats
        print('Waiting for the wireless endpoint to be communicating with the server')
        time.sleep(2)

        # Get the results on the wireless endpoint
        print('Fetching the results')
        self.wireless_endpoint.ResultGet()

        print('Parsing the results')
        history = network_info_monitor.ResultHistoryGet()
        history.Refresh()

        # Collect the results
        headers = (
            '"Time"',
            '"SSID"',
            '"BSSID"',
            '"Channel"',
            '"RSSI (dBm)"',
            '"Tx Rate (bps)"'
        )
        results = []
        for interval in history.IntervalGet():
            interfaces = interval.InterfaceGet()

            network_interface = None
            for interface in interfaces:
                if interface.DisplayNameGet() == self.wireless_interface:
                    network_interface = interface

            if network_interface is None:
                print("No interface found for", self.wireless_interface)

            result = (
                interval.TimestampGet(),
                "\"" + network_interface.WiFiSsidGet() + "\"",
                "\"" + network_interface.WiFiBssidGet() + "\"",
                network_interface.WiFiChannelGet(),
                network_interface.WiFiRssiGet(),
                network_interface.WiFiTxRateGet()
            )

            results.append(result)

        self.wireless_endpoint.Lock(False)

        return headers, results

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
        headers, results = example.run()
    finally:
        example.cleanup()

    with open("network_info_monitor_test.csv", "w") as f:
        f.write(";".join(headers) + '\n')
        for result in results:
            f.write(";".join([str(item) for item in result]) + '\n')
    print("results written to network_info_monitor_test.csv")

