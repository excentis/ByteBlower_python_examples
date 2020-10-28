"""
    This example shows you how to perform a DNS request.

    It demonstrates:
      * Howto craft a custom packet using SCAPY.
      * Transmit it using ByteBlower
      * Capture the answer and dissect it.
      * Time the whole process.

   This example is fully runnable. It needs 3 arguments:
       <ByteBlower Server Address> <ByteBlower Interface> <Domain name> 
"""
import byteblowerll.byteblower as byteblower
from scapy.all import *
import time

import sys

if len(sys.argv) != 4:
    help_txt = """This script requires following arguments.
       <ByteBlower Server Address> <ByteBlower Interface> <Domain name> 
       It received: %s""" % sys.argv[1:]
    print(help_txt)    
    sys.exit(-1)


bb_server_address, bb_interface, query = sys.argv[1:]

# ByteBlower part.
api = byteblower.ByteBlower.InstanceGet()
server = api.ServerAdd(bb_server_address)

# Query and DNS Config
dns_server = '8.8.8.8'
port_mac = '00:BB:23:21:55:12'

port = server.PortCreate(bb_interface)
l2 = port.Layer2EthIISet()
l2.AddressSet(port_mac)

l3 = port.Layer3IPv4Set()
l3.ProtocolDhcpGet().Perform()
my_ip = l3.IpGet()

# Create the DNS request.
resolved_mac = l3.Resolve(dns_server)

stream = port.TxStreamAdd()
bb_frame = stream.FrameAdd()
sc_frame = Ether(src=port_mac, dst=resolved_mac) / IP(src=my_ip, dst=dns_server)/UDP(dport=53)/DNS(rd=1,qd=DNSQR(qname=query))
frameContent = bytearray(bytes(sc_frame))
hexbytes = ''.join((format(b, "02x") for b in frameContent))

# Prepare for receiving the response 
cap = port.RxCaptureBasicAdd()
cap.FilterSet('ip and udp dst port 53')
cap.Start()

# Do the request
bb_frame.BytesSet(hexbytes)
stream.NumberOfFramesSet(1)
stream.InterFrameGapSet(1000 * 1000)

stream.Start()

# Wait for the response
while True:
    sniffed = cap.ResultGet()
    sniffed.Refresh()

    if sniffed.PacketCountGet() > 0:
        break

    time.sleep(0.01)

cap.Stop()

# Process the response.

# When was the frame transmitted?
stream.ResultHistoryGet().Refresh()
start_time = stream.ResultHistoryGet().CumulativeLatestGet().TimestampLastGet()

for f in sniffed.FramesGet():
    response_moment = f.TimestampGet()
    data = ''.join([chr(b) for b in f.BufferGet()])
    raw = Ether(data)
    dns_response = raw.lastlayer()

    response_code = dns_response.getfieldval('rcode')
    print("Queried %s for '%s'" % (dns_server, query))
    if response_code == 0:
        duration = (response_moment - start_time) / 1e6
        print("Response: %s in %f ms" % 
                (dns_response.getfieldval('an'). getfieldval('rdata'),
                  duration))
    else:        
        print('Record not found')
