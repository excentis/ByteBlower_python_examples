"""
    This script discovers what is connected to your ByteBlower.
    Optionally you can limit which interfaces are scanned. 

    The discovery process is following, on each participating port
      * Configure the ByteBlower port through DHCP.
         This gives us not only an IP address but also
         the address of the gateway for this port.
      * Get the MAC address of the gateway.
         This done through ARP.
      * Lookup up to the MAC to known whom it belongs to
         We use http://macvendors.co to the vendors.
"""
from __future__ import print_function

import sys
import random
import codecs
import json
import urllib2

from byteblowerll.byteblower import ByteBlower
from byteblowerll.byteblower import DHCPFailed
from byteblowerll.byteblower import AddressResolutionFailed

def a_mac_address():
    """
        Generates a MAC address
    """
    byte_vals = (
        ["00", "bb"] + ["%2x" % random.randint(0, 255) for _ in xrange(4)])
    return ":".join(byte_vals)


def lookup_vendor_name(mac_address):
    """
        Translates the returned mac-address to a vendor
    """

    url = "http://macvendors.co/api/%s" % mac_address
    request = urllib2.Request(url, headers={'User-Agent': "API Browser"})
    try:
        response = urllib2.urlopen(request)

        reader = codecs.getreader("utf-8")
        obj = json.load(reader(response))
        response.close()
        return obj['result']['company']
    except urllib2.URLError:
        return "Unable to lookup MAC address"
    except KeyError:
        return "MAC lookup API changed"


def inspect_trunk(server, trunkbase =''):
    """
        Inspect a trunk-interface of a server to detect connected modems
    """
    byteblower_instance = ByteBlower.InstanceGet()
    server = byteblower_instance.ServerAdd(server)

    ports = []
    for an_bb_interface in server.InterfaceNamesGet():
        if not an_bb_interface.startswith(trunkbase):
            continue

        port = server.PortCreate(an_bb_interface)
        port_l2 = port.Layer2EthIISet()
        port_l2.MacSet(a_mac_address())

        port_l3 = port.Layer3IPv4Set()
        port_l3.ProtocolDhcpGet().PerformAsync()
        ports.append(port)

    responding_ports = []
    for a_port in ports:
        try:
            l3 = a_port.Layer3IPv4Get()
            dhcp = l3.ProtocolDhcpGet()
            dhcp.Perform()
            l3.ResolveAsync(l3.GatewayGet())
            responding_ports.append(a_port)
        except DHCPFailed:
            server.PortDestroy(a_port)

    for a_port in responding_ports:
        l3 = a_port.Layer3IPv4Get()
        gateway_addr = l3.GatewayGet()
        try:
            mac_gw = l3.Resolve(gateway_addr)
            vendor_string = lookup_vendor_name(mac_gw)

            result_format = "%s, %s, %s, %s"
            print(result_format % (a_port.InterfaceNameGet(), l3.IpGet(),
                                    mac_gw, vendor_string))
        except AddressResolutionFailed:
            pass

        server.PortDestroy(a_port)

if __name__ == "__main__":
    if not (2 <= len(sys.argv) <= 3):
        print('Expects at least arguments: <server address>')
        print(' An optional second argument allows you to filter the ports you whish to scan')
        print (' Got following arguments: ' + ', '.join(sys.argv[1:]))

        sys.exit(-1)

    server = sys.argv[1]
    if len(sys.argv) == 3:
        base_string = sys.argv[2]
        print('Using base_string ' + base_string)
    else:
        base_string = ''

    inspect_trunk(server, base_string)
