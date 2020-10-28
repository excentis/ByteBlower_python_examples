"""
    This example shows how to ping a modem connected to the ByteBlower switch.

    For educational reasons this example is kept fairly brief.
      * The source port is configured through DHCP.
      * We ping to a fixed IP address. 
      * The results are printed to stdout.

    All available options on how to configure an IP address to a
    Byteblower port is found elsewhere.

    Also good to remember, a ByteBlower will also respond to ICMP ping
    messages. It does this as soon as the IPv4 layer is configured.

"""
import time
import sys

import byteblowerll.byteblower as bb


def create_port(server, bb_interface):
    port = server.PortCreate(bb_interface)

    l2 = port.Layer2EthIISet()
    l2.MacSet('00-bb-ff-01-02-13')

    l3 = port.Layer3IPv4Set()
    l3.ProtocolDhcpGet().Perform()

    return port


def do_ping(port, target_address):
    """
        Performs 5 pings and prints them to stdout.
    """
    l3 = port.Layer3IPv4Get()
    my_ip = l3.IpGet()

    icmp = l3.ProtocolIcmpGet()
    ping_session = icmp.SessionAdd()
    ping_session.RemoteAddressSet(target_address)
    ping_session.EchoLoopIntervalSet(10**9)
    ping_session.EchoLoopStart()

    for ping_cnt in range(5):
        time.sleep(1.1)
        ping_session.Refresh()
        print("Ping from %s to %s" % (my_ip, target_address))
        print(ping_session.SessionInfoGet().DescriptionGet())
        print('')


def main(server_address, bb_interface, target_address):
    api = bb.ByteBlower.InstanceGet()
    server = None
    try:
        server = api.ServerAdd(server_address)
        port = create_port(server, bb_interface)
        do_ping(port, target_address)

    finally:
        if server is not None:
            api.ServerRemove(server)


if __name__ == '__main__':
    if len(sys.argv) != 4:
        print('This script expects 3 arguments:')
        print('   <server address> <byteblower interface> <IP to ping>')
        print(' but got: ' + ', '.join(sys.argv[1:]))
        sys.exit(-1)

    main(server_address=sys.argv[1], bb_interface=sys.argv[2],
         target_address=sys.argv[3])
