#!/usr/bin/python
import byteblowerll.byteblower as byteblower
import sys

try:
    instance = byteblower.ByteBlower.InstanceGet()
    assert isinstance(instance, byteblower.ByteBlower)

    # Connect to the meetingpoint
    #meetingpoint = instance.MeetingPointAdd(sys.argv[2])
    meetingpoint = instance.MeetingPointAdd(sys.argv[2])

    weList = meetingpoint.DeviceListGet()
    for we in weList:
        print (we.DeviceInfoGet().GivenNameGet() + "  Battery Level: " + str(we.DeviceInfoGet().BatteryLevelGet()))
except Exception as e:
    print("Caught Exception: " + str(e))