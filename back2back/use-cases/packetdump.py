#!/usr/bin/python
from __future__ import print_function
import byteblowerll.byteblower as byteblower
import time


def capture(server_address, interface, filename):
    byteblower_instance = byteblower.ByteBlower.InstanceGet()

    bb_server = None
    try:
        bb_server = byteblower_instance.ServerAdd(server_address)
        port = bb_server.PortCreate(interface)

        interface = port.GetByteBlowerInterface()
        packet_dump = interface.PacketDumpCreate()
        packet_dump.Start(filename)
        while (packet_dump.FileSizeGet()) < 1000000000:
            time.sleep(10)
        packet_dump.Stop()

        print("Finished")

    except byteblower.DomainError as e:
        print("Caught DomainError: " + e.getMessage())
        return 1

    except byteblower.TechnicalError as e:
        print("Caught TechnicalError: " + e.getMessage())
        return 1

    except Exception as e:
        print("Caught Exception: " + str(e))
        return 1

    finally:
        if bb_server is not None:
            byteblower_instance.ServerRemove(bb_server)


if __name__ == '__main__':
    import sys
    sys.exit(capture('byteblower-tutorial-1300.lab.byteblower.excentis.com', 'nontrunk-1', 'packetdump.pcap'))
