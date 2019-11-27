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

    # Address (IP or FQDN) of the ByteBlower Meetingpoint to use.  The wireless endpoint *must* be registered
    # on this meetingpoint.
    'meetingpoint_address': 'byteblower-dev-4100-1.lab.byteblower.excentis.com',

    # UUID of the ByteBlower WirelessEndpoint to use.  This wireless endpoint *must* be registered to the meetingpoint
    # configured by meetingpoint_address.
    # Special value: None.  When the UUID is set to None, the example will automatically select the first available
    # wireless endpoint.
    # 'wireless_endpoint_uuid': None,
    'wireless_endpoint_uuid': '6d9c2347-e6c1-4eea-932e-053801de32eb',

    # Name of the Interface as given by the operating system.
    'wireless_interface': 'Intel(R) Dual Band Wireless-AC 8265',

    # duration in seconds to poll for information
    'duration_s': 10,
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
        network_info = device_info.NetworkInfoGet()
        interfaces = network_info.InterfaceGet()

        network_interface = None
        for network_interface in interfaces:
            if network_interface.DisplayNameGet() == self.wireless_interface:
                break

        if network_interface is None:
            print("ERROR: could not find the specified interface")
            return 1

        from byteblowerll.byteblower import NetworkInterface
        assert isinstance(network_interface, NetworkInterface)

        headers = (
            '"SSID"',
            '"BSSID"',
            '"Channel"',
            '"RSSI (dBm)"',
            '"Tx Rate (bps)"'
        )
        results = []
        for _ in range(self.duration_s):
            network_info.Refresh()
            print(network_interface.DisplayNameGet())
            result = (
                "\"" + network_interface.WiFiSsidGet() + "\"",
                "\"" + network_interface.WiFiBssidGet() + "\"",
                network_interface.WiFiChannelGet(),
                network_interface.WiFiRssiGet(),
                network_interface.WiFiTxRateGet()
            )

            results.append(result)
            time.sleep(1)

        with open("network_info_test.csv", "w") as f:
            f.write(";".join(headers) + '\n')
            for result in results:
                f.write(";".join([str(item) for item in result]) + '\n')
        print("results written to network_info_test.csv")

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
