#!/usr/bin/python
""""
 This example demonstrates polling the Wi-Fi statistics from a Wireless Endpoint.

The polling method is on of the two ways of the getting this info. Compared to the
Wi-Fi monitor it has these differences:

 * The Wireless Endpoint stays available for aynone to use.
    Multple programs can poll the results at the same time.
 * The methods return immediately. There are no blocking calls.
 * The returned Wi-Fi statistics are only updated while the 
    wireless endpoint is heartbeating. They are thus not 
    the live results.
 *  During a testrun the Wireless Endpoint isn't heartbeating.
    There are thus alos no updates of the results at this time.
    You can still retrieve the old values though.

We recommend using the polling method for basic monitoring of
your Wireless Endpoints. 

"""

from __future__ import print_function
import time
# We want to use the ByteBlower python API, so import it
from byteblowerll.byteblower import ByteBlower

configuration = {

    # Address (IP or FQDN) of the ByteBlower Meetingpoint to use.  The wireless endpoint *must* be registered
    # on this meetingpoint.
    'meetingpoint_address': 'byteblower-dev-4100-2.lab.byteblower.excentis.com',

    # UUID of the ByteBlower WirelessEndpoint to use.  This wireless endpoint *must* be registered to the meetingpoint
    # configured by meetingpoint_address.
    # Special value: None.  When the UUID is set to None, the example will automatically select the first available
    # wireless endpoint.
    # 'wireless_endpoint_uuid': None,
    'wireless_endpoint_uuid': None,

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
            self.wireless_endpoint_uuid = self.select_an_wireless_endpoint_uuid()

        # Get the WirelessEndpoint device
        # We don't need to lock the Wireless Endpoint to get the polling results.
        self.wireless_endpoint = self.meetingpoint.DeviceGet(self.wireless_endpoint_uuid)
        print("Using wireless endpoint", self.wireless_endpoint.DeviceInfoGet().GivenNameGet())

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

        csv_headers = (
            '"SSID"',
            '"BSSID"',
            '"Channel"',
            '"RSSI (dBm)"',
            '"Tx Rate (bps)"'
        )
        results = []
        for _ in range(self.duration_s):
            network_info.Refresh()
            result = (
                "\"" + network_interface.WiFiSsidGet() + "\"",
                "\"" + network_interface.WiFiBssidGet() + "\"",
                network_interface.WiFiChannelGet(),
                network_interface.WiFiRssiGet(),
                network_interface.WiFiTxRateGet()
            )
            print(network_interface.DisplayNameGet(), result)

            results.append(result)
            time.sleep(1)

        with open("network_info_test.csv", "w") as f:
            f.write(";".join(csv_headers) + '\n')
            for result in results:
                f.write(";".join([str(item) for item in result]) + '\n')
        print("results written to network_info_test.csv")

        instance.MeetingPointRemove(self.meetingpoint)

    def select_an_wireless_endpoint_uuid(self):
        """
        Finds an available Wireless Endpoint to use.

        :return: a string representing the UUID or None when no device is available.
        """
        from byteblowerll.byteblower import DeviceStatus_Available

        for device in self.meetingpoint.DeviceListGet():
            if device.StatusGet() == DeviceStatus_Available:
                # yes, return the UUID
                return device.DeviceIdentifierGet()

        # No device found, return None
        return None


if __name__ == '__main__':
    Example(**configuration).run()
