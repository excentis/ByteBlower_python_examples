"""
Basic IPv4 Example for the ByteBlower Python API.
All examples are garanteed to work with Python 2.7 and above

Copyright 2016, Excentis N.V.
"""

# Needed for python2 / python3 print function compatibility
from __future__ import print_function

# import the ByteBlower module
import byteblowerll.byteblower as byteblower

# import the configuration for this example
from ipv4_conf import *

from example_generic import create_port, create_flow_ipv4_udp

import time


def run():
    
    byteblower_instance = byteblower.ByteBlower.InstanceGet()
    
    print("Connecting to ByteBlower server {}...".format(serverAddress))
    server = byteblower_instance.ServerAdd(serverAddress)
    
    srcPort = create_port(server, physicalPort1, srcMacAddress1, "ipv4", srcPerformDhcp1, srcIpAddress1, srcNetmask1, srcIpGW1)
    
    dstPort = create_port(server, physicalPort2, dstMacAddress1, "ipv4", dstPerformDhcp1, dstIpAddress1, dstNetmask1, dstIpGW1)
    
    print("Current source port configuration:\n{}".format(srcPort.DescriptionGet()))
    print("Current destination port configuration:\n{}".format(dstPort.DescriptionGet()))
    
    if ethernetLength > srcPort.MDLGet():
        print("Source Port: Setting MTU to {}".format(ethernetLength))
        srcPort.MDLSet(ethernetLength)

    if ethernetLength > dstPort.MDLGet():
        print("Destination Port: Setting MTU to {}".format(ethernetLength))
        dstPort.MDLSet(ethernetLength)
        
    (stream,trigger) = create_flow_ipv4_udp(srcPort, dstPort, ethernetLength, srcUdpPort1, dstUdpPort1, numberOfFrames, interFrameGap)
    
    if bidir:
        # When sending bi-directional, the sources become the destinations
        # and vice versa.
        (stream2,trigger2) = create_flow_ipv4_udp(dstPort, srcPort, ethernetLength, dstUdpPort1, srcUdpPort1, numberOfFrames, interFrameGap)

    # Remove any packets received already and start the streams
    trigger.ResultClear()
    stream.Start()

    
    if bidir:
        trigger2.ResultClear()    
        stream2.Start()
    
    # Calculate how long to wait before are frames are sent.  The formula is
    # interframegap * number_of_frames, 
    # where the interframegap is the time between the start of transmission 
    # of 2 consecutive frames (in nanoseconds).
    # Since time.sleep() has a one second unit, we have to divide the number by
    # the number of nanoseconds per second, which is 1000000000.
    timeToSleep = (interFrameGap * numberOfFrames * 1.0 ) / 1000000000
    print("Will sleep for",timeToSleep,"s , so all frames can be sent...")
    time.sleep(timeToSleep)
    
    stream.Stop()
    if bidir:
        stream2.Stop()
    
    # Wait 1 second here, this will ensure that frames which were in transit are
    # still triggered by the trigger
    time.sleep(1)
    
    # Get the results for the first stream and trigger.
    triggerResult = trigger.ResultGet()
    streamResult = stream.ResultGet()

    triggerResult.Refresh()
    streamResult.Refresh()
 
    if bidir:
        # Get the bi-directional results
        triggerResult2 = trigger2.ResultGet()
        streamResult2 = stream2.ResultGet()
        
        triggerResult2.Refresh()
        streamResult2.Refresh()

    result = []
     
    txPacketCount = streamResult.PacketCountGet()
    loss = ( ( txPacketCount - triggerResult.PacketCountGet() ) * 100.0 ) / txPacketCount if txPacketCount else 0.0
    result.append(loss)
    if bidir:
        txPacketCount2 = streamResult2.PacketCountGet()
        loss2 = ( ( txPacketCount2 - triggerResult2.PacketCountGet() ) * 100.0) / txPacketCount2 if txPacketCount2 else 0.0
        result.append(loss2)
        
    print("Frame loss:", loss)
    print("Frame loss2:", loss2)

    return result
    

# When this python module is called stand-alone, the run-function must be
# called.  This approach makes it possible to include it in a series of
# examples.
if __name__ == "__main__":
    result = run()
