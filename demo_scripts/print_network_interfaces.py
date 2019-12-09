#!/usr/bin/python
import byteblowerll.byteblower as byteblower
import sys


def get_network_interfaces_for_device(device):
    return device.DeviceInfoGet().NetworkInfoGet().DescriptionGet() + "\n"


def get_network_interfaces(server_address, uuid=None):
    instance = None
    meetingpoint = None

    output = ""
    try:
        instance = byteblower.ByteBlower.InstanceGet()
        assert isinstance(instance, byteblower.ByteBlower)

        # Connect to the meetingpoint
        meetingpoint = instance.MeetingPointAdd(server_address)

        if uuid is None:
            for device in meetingpoint.DeviceListGet():
                output += "Device: " + device.DeviceInfoGet().GivenNameGet() + ":"
                output += get_network_interfaces_for_device(device)
        else:
            device = meetingpoint.DeviceGet(uuid)
            output += get_network_interfaces_for_device(device)

    except Exception as e:
        print("Caught Exception: " + str(e))

    finally:
        if instance is not None and meetingpoint is not None:
            instance.MeetingPointRemove(meetingpoint)

    return output


if __name__ == '__main__':
    if 2 > len(sys.argv) > 3:
        print("ERROR: Expecting address of the server to connect to:")
        print("  USAGE: {} <server_address> [wireless_endpoint_uuid]".format(sys.argv[0]))
        sys.exit(1)

    we_uuid = None
    if len(sys.argv) == 3:
        we_uuid = sys.argv[2]

    print(get_network_interfaces(sys.argv[1]), we_uuid)
