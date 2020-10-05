#!/usr/bin/python
"""
    This script lists all Wireless Endpoints registered to a MeetingPoint.

    We print out the name of the device together with its UUID.

    You can run this script immediately in Python. It has a sole argument,
    the address of the meetingpoint to scan.

    Example:
    =======
        Input:
        ---
        python print_device_names.py 10.8.254.11

        Output:
        ---
        POOL-004, 00eb9569-944e-4e76-8ce9-e45332db690e
        laptop-028, 502d62e8-853f-496b-990b-731f25012f33
        Samsung Galaxy S7, 77e707a123381475


"""
from __future__ import print_function
import byteblowerll.byteblower as byteblower
import sys


def get_device_info(server_address):
    output = ""
    instance = None
    meetingpoint = None
    try:
        instance = byteblower.ByteBlower.InstanceGet()
        assert isinstance(instance, byteblower.ByteBlower)

        # Connect to the meetingpoint
        meetingpoint = instance.MeetingPointAdd(server_address)

        wireless_endpoints = meetingpoint.DeviceListGet()
        for we in wireless_endpoints:
            fmt = "{NAME}, {UUID}"
            line = fmt.format(NAME=we.DeviceInfoGet().GivenNameGet(),
                              UUID=we.DeviceIdentifierGet())
            output += line + "\n"

    except Exception as e:
        print("Caught Exception:", str(e))

    finally:
        if instance is not None and meetingpoint is not None:
            instance.MeetingPointRemove(meetingpoint)

    return output


if __name__ == '__main__':
    meetingpoint = 'byteblower-tutorial-1300.lab.byteblower.excentis.com'
    if len(sys.argv) != 2:
        print("Usage: {} <server_address>".format(sys.argv[0]))
        print("Connecting to: {}".format(meetingpoint))
        print()
    else:    
        meetingpoint = sys.argv[1]
        
    print(get_device_info(meetingpoint))
