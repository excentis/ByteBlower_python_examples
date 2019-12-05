#!/usr/bin/python
import byteblowerll.byteblower as byteblower
import sys

try:
    instance = byteblower.ByteBlower.InstanceGet()
    assert isinstance(instance, byteblower.ByteBlower)

    # Connect to the meetingpoint
    meetingpoint = instance.MeetingPointAdd("byteblower-tutorial-1300.lab.byteblower.excentis.com")

    wirelessEndpoint = meetingpoint.DeviceGet("65e298b8-5206-455c-8a38-6cd254fc59a2")

    print(wirelessEndpoint.DeviceInfoGet().NetworkInfoGet().DescriptionGet())

except Exception as e:
    print("Caught Exception: " + str(e))