from byteblowerll.byteblower import ByteBlower

import urllib2
import json
import codecs


"""
This script will scan all ports of a ByteBlower trunk (1 till 48 ) and try to discover the connected modem.

How: It will try to arp 192.168.100.1 on each port which is the default gw ip of a modem (Cable-Modem). The mac-address is translated to a vendor



"""

#Change if needed
MODEM_DEFAULT_IP = "192.168.100.1"

TEST_IP = "192.168.100.100"
TEST_MAC = "00ff1c000004"

SERVER = "byteblower-tutorial-1300.lab.byteblower.excentis.com"
TRUNK_BASE = "trunk-1" # base of the trunk; e.g. trunk-1 or trunk-2

"""
Translate the returned mac-address to a vendor
"""
def fetchVendor(mac):

    #API base url,you can also use https if you need
    url = "http://macvendors.co/api/"
    #Mac address to lookup vendor from
    mac_address = mac

    request = urllib2.Request(url+mac_address, headers={'User-Agent' : "API Browser"})
    response = urllib2.urlopen( request )
    #Fix: json object must be str, not 'bytes'
    reader = codecs.getreader("utf-8")
    obj = json.load(reader(response))
    return obj['result']['company']


"""
Inspect a trunk-interface of a server to detect connected modems
"""
def inspectTrunk(server,trunkbase):
    byteblower_instance = ByteBlower.InstanceGet()


    server = byteblower_instance.ServerAdd(server)
    trunkport=trunkbase+"-"
    mapping = []
    for x in range(1,49):
        p = trunkport+str(x)
        port = server.PortCreate(p)
        port_l2 = port.Layer2EthIISet()
        port_l2.MacSet(TEST_MAC)
        port_l3 = port.Layer3IPv4Set()
        port_l3.IpSet(TEST_IP)
        port_l3.NetmaskSet("255.255.255.0")
        port_l3.GatewaySet(MODEM_DEFAULT_IP)
        port_l3.ResolveAsync(MODEM_DEFAULT_IP)
        mapping.append(port)

    for trunk in mapping:
        try :
            mac = trunk.Layer3IPv4Get().Resolve(MODEM_DEFAULT_IP)
            print trunk.InterfaceNameGet() + ": " + fetchVendor(mac) + " - " + mac
        except :
            print trunk.InterfaceNameGet() + ":"
        server.PortDestroy(trunk)


inspectTrunk(SERVER,TRUNK_BASE)
