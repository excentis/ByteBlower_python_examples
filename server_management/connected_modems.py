"""
    This script will scan all ports of a ByteBlower trunk (1 till 48 ) and try to discover the connected modem.

    How: It will try to arp 192.168.100.1 on each port which is the default gw ip of a modem (Cable-Modem).
    The mac-address is translated to a vendor
"""
from __future__ import print_function

import random
import codecs
import json
import urllib2

from byteblowerll.byteblower import ByteBlower
from byteblowerll.byteblower import DHCPFailed
from byteblowerll.byteblower import AddressResolutionFailed


def a_mac_address():
    byte_vals = (
        ["00", "bb"] + ["%2x" % random.randint(0, 255) for _ in xrange(4)])
    return ":".join(byte_vals)


SERVER = "byteblower-tutorial-3100.lab.byteblower.excentis.com"
TRUNK_BASE = "trunk-1"  # base of the trunk; e.g. trunk-1 or trunk-2


def lookup_vendor_name(mac_address):
    """
        Translates the returned mac-address to a vendor
    """
    # API base url,you can also use https if you need
    url = "http://macvendors.co/api/%s" % mac_address

    request = urllib2.Request(url, headers={'User-Agent': "API Browser"})
    response = urllib2.urlopen(request)

    # Fix: json object must be str, not 'bytes'
    reader = codecs.getreader("utf-8")
    obj = json.load(reader(response))
    return obj['result']['company']


def inspect_trunk(server, trunkbase):
    """
        Inspect a trunk-interface of a server to detect connected modems
    """

    byteblower_instance = ByteBlower.InstanceGet()

    server = byteblower_instance.ServerAdd(server)
    ports = []
    for an_bb_interface in server.InterfaceNamesGet():
        if not TRUNK_BASE in an_bb_interface:
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

    for trunk in responding_ports:
        l3 = trunk.Layer3IPv4Get()
        gateway_addr = l3.GatewayGet()
        try:
            mac = l3.Resolve(gateway_addr)

            result = "%s, %s, %s, %s" % (trunk.InterfaceNameGet(), l3.IpGet(),
                                         mac, lookup_vendor_name(mac))
            print(result)
        except AddressResolutionFailed:
            pass

        server.PortDestroy(trunk)


inspect_trunk(SERVER, TRUNK_BASE)
