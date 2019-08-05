#!/usr/bin/python
import byteblowerll.byteblower as byteblower
import time

try:
    bbServer = byteblower.ByteBlower.InstanceGet().ServerAdd("byteblower-tutorial-1300.lab.byteblower.excentis.com")
    port = bbServer.PortCreate("nontrunk-1")

    interface = port.GetByteBlowerInterface()
    packetDump = interface.PacketDumpCreate()
    packetDump.Start("packetDump.pcap")
    while (packetDump.FileSizeGet()) < 1000000000:
        time.sleep(10)
    packetDump.Stop()

    print("Finished")

except byteblower.DomainError as e:
    print "Caught DomainError: " + e.getMessage()

except byteblower.TechnicalError as e:
    print "Caught TechnicalError: " + e.getMessage()
except ValueError as e:
    print str(e)
except Exception as e:
    print "Caught Exception: " + e.getMessage()
