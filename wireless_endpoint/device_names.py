#!/usr/bin/python
from __future__ import print_function
import byteblowerll.byteblower as byteblower
import sys


def print_device_info(server_address):
    try:
        instance = byteblower.ByteBlower.InstanceGet()
        assert isinstance(instance, byteblower.ByteBlower)

        # Connect to the meetingpoint
        meetingpoint = instance.MeetingPointAdd(server_address)

        wireless_endpoints = meetingpoint.DeviceListGet()
        for we in wireless_endpoints:
            print(we.DeviceInfoGet().GivenNameGet() + "  Battery Level: " + str(we.DeviceInfoGet().BatteryLevelGet()))

    except Exception as e:
        print("Caught Exception: " + str(e))


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("ERROR: Expecting address of the server to connect to:")
        print("  USAGE: {} <server_address>".format(sys.argv[0]))
        sys.exit(1)

    sys.exit(print_device_info(sys.argv[1]))
