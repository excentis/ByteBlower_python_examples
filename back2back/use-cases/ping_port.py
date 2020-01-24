"""
    This example shows how to ping a modem connected
    to the ByteBlower switch.

    For educational reasons this example is kept fairly
    brief. 
      * The source port is configured through DHCP.
      * We ping to a fixed IP address. 
      * The results are printed to stdout.

    All available options on how to configure an IP
    address to a Byteblower port is found elsewhere.

    Also good remember, a ByteBlower will also respond
    to Ping messages. It does this as soons as the 
    IPV4 layer is configured.
    """
import time
import sys

import byteblowerll.byteblower as bb

BB_SERVER = 'byteblower-tp-4100.lab.byteblower.excentis.com'
BB_INTERFACE = 'trunk-1-13'

MODEM_IP_ADDR  = '10.8.253.11'

def create_port(server, bb_interface):
    port = server.PortCreate(BB_INTERFACE)

    l2 = port.Layer2EthIISet()
    l2.MacSet('00-bb-ff-01-02-13')

    l3 = port.Layer3IPv4Set()
    l3.ProtocolDhcpGet().Perform()

    return port

           

def do_ping(server_address, bb_interface, target_address):
    api = bb.ByteBlower.InstanceGet()
    server = api.ServerAdd(BB_SERVER)
    port = create_port(server, bb_interface)

    l3 = port.Layer3IPv4Get()
    my_ip = l3.IpGet()

    icmp = l3.ProtocolIcmpGet()
    ping_session = icmp.SessionAdd()
    ping_session.RemoteAddressSet(MODEM_IP_ADDR)
    ping_session.EchoLoopIntervalSet(10 ** 9)
    ping_session.EchoLoopStart()

    for ping_cnt in range(5):
        time.sleep(1.1)
        ping_session.Refresh()
        print("Ping from %s to %s" % (my_ip, target_address))
        print(ping_session.SessionInfoGet().DescriptionGet())
        print('')
 
    api.ServerRemove(server)

do_ping(BB_SERVER, BB_INTERFACE, MODEM_IP_ADDR)
