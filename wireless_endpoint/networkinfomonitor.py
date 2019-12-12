#!/usr/bin/python
""""
This example collect the Wi-Fi statistics as they change in real-time.

The get these values we use an Wi-Fi monitor. This approach is different
for the polling approach is in following aspects:

    * The Wi-Fi statistics are collected at a regular interval,
      Default values are updated every second, much more frequent
       than is possible through the polling approach.

    * The Network monitor is always part of a scenario on a Wireless 
       Endpoint. This has a large impact:
          - In the same scenario you can add other traffic (TCP or FrameBlasting).
          - While the scenario is running, the Wireless Endpoint maintains
             radio silence you can't communicate with it.
          - A scenario is always locked to a single API connection.
          - It takes a couple Wireless Endpoint heartbeat to start/finish a scenario. 
          - The collected results are only available after the testrun has finished.
    
    * If your device has multiple Wi-Fi network adapters, the statistics are logged
       simultaneously on all network interfaces. 

    * The NetworkMonitor is more complex to use compared to the polling method. 
       This is especially when you are only interested indiciative values for
       the Wi-Fi statistics.
  
We recommend using the NetworkInfoMonitor when you want to collect results:
   * During a test run.
   * Wish to have very regular, time-stamped measurements. 

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
    'wireless_endpoint_uuid': None,
    # 'wireless_endpoint_uuid': '86B6D1A7-72D0-4462-B8D0-ED5655F906CC',

    # Name of the Interface as given by the operating system.
    # For education purposes, when the interface isn't found we
    #  we will take any other device.
    'wireless_interface': 'en0',

    # duration in seconds to poll for information
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

        # If no WirelessEndpoint UUID was given, search for any available one.
        if self.wireless_endpoint_uuid is None:
            self.wireless_endpoint_uuid = self.select_wireless_endpoint_uuid()

        # Get the WirelessEndpoint device
        self.wireless_endpoint = self.meetingpoint.DeviceGet(self.wireless_endpoint_uuid)
        print("Using wireless endpoint", self.wireless_endpoint.DeviceInfoGet().GivenNameGet())

        # The network monitor is part of scenario.
        self.wireless_endpoint.Lock(True)
        self.wireless_endpoint.ScenarioDurationSet(self.duration_s * 1000000000)  # ns

        # Add the monitor to the scenario.
        # The Wi-Fi statistics are captured as soon as the scenario starts.
        device_info = self.wireless_endpoint.DeviceInfoGet()
        network_info_monitor = device_info.NetworkInfoMonitorAdd()
        
        # Start the test-run.
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

        # Collect the results from the NetworkInfoMonitor
        csv_headers = (
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
            for network_interface in interfaces:
                if network_interface.DisplayNameGet() == self.wireless_interface:
                    break

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

        return csv_headers, results

    def cleanup(self):
        instance = ByteBlower.InstanceGet()

        if self.meetingpoint is not None:
            instance.MeetingPointRemove(self.meetingpoint)

    def select_wireless_endpoint_uuid(self):
        """
        Finds an available Wireless Endpoint on the MeetingPoint 

        :return: a string representing the UUID or None
        """
        from byteblowerll.byteblower import DeviceStatus_Available

        for device in self.meetingpoint.DeviceListGet():
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

