"""
    This example performs a DHCP request and captures simulatenously captures
    DHCP packets.

    It demonstrates:
      * Howto perform a DHCP request. 
      * Howto capture the packets.

   This example is fully runnable. It needs 3 arguments:
       <ByteBlower Server Address> <ByteBlower Interface> <filename to save to> 
"""
import byteblowerll.byteblower as byteblower
import time

import sys

if len(sys.argv) != 4:
    help_txt = """This script requires following arguments.
       <ByteBlower Server Address> <ByteBlower Interface> <filename to save to> 
       It received: %s""" % sys.argv[1:]
    print(help_txt)    
    sys.exit(-1)


bb_server_address, bb_interface, capture_filename = sys.argv[1:]

## ByteBlower part.
api = byteblower.ByteBlower.InstanceGet()
server = api.ServerAdd(bb_server_address)

port_mac = '00:BB:23:21:55:12'

port = server.PortCreate(bb_interface)
capture = server.PacketDumpCreate(bb_interface)
capture.Start(capture_filename)

l2 = port.Layer2EthIISet()
l2.AddressSet(port_mac)

l3 = port.Layer3IPv4Set()
l3.ProtocolDhcpGet().Perform()
my_ip = l3.IpGet()

print('Received IP address: %s' % my_ip)

time.sleep(2)
capture.Stop()
api.ServerRemove(server)
