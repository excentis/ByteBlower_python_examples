#!/usr/bin/python
""""
 This example demonstrates polling the Wi-Fi statistics

 The main goal of the script is teaching how the API works. We will print
  out the results to screen. For a more involved demo we suggest to 
  look into the demo folder (toplevel)

 Polling the Network Info is one of the two ways to get the Wi-Fi
  statistics. The Wi-Fi monitor is the other one. They have following
  differences:

 * The polling method returns the Wi-Fi statistics cached in the 
    MeetingPoint. These values are updated every several
    heartbeats. It can take up to a minute for a change to propagate. 

 * With the Polling method, the Wi-Fi statistics can be retrieved
    without locking the Wireless Endpoint. The WEP remains available
    for anyone to use.

 * The polling methods return immediately. There are no blocking calls
    In addition all error handling is delegated to the MeetingPoint.
    This makes the polling approach much easier to use.

 * During a testrun the Wireless Endpoint isn't heartbeating.
    There are thus alos no updates of the results at this time.
    You can still retrieve the old values though.

 We recommend using the polling method when indicative
  Wi-Fi statistics are sufficient (e.g. displaying the value to 
  a user), when there's only interest in changes over several
   minutes (e.g. monitoring).

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
    # The script will pick another interface when this one isn't
    # found.
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

        if self.wireless_endpoint_uuid is None:
            print("The MeetingPoint has no available Wireless Endpoints. Aborting the example.")
            return

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

        headers = (
            '"SSID"',
            '"BSSID"',
            '"Channel"',
            '"RSSI (dBm)"',
            '"Tx Rate (bps)"'
        )
        results = []
        for _ in range(self.duration_s):
            # Synchronize the local API object with the values 
            #  cached in the MeetingPoint
            network_info.Refresh()

            # Collect the results and print them out.
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
