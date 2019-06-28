"""
    A simple example of NAT performance testing.

    It will generate multiple short TCP sessions for a configured duration.


"""

from __future__ import print_function
import byteblowerll.byteblower as byteblower
from byteblowerll.byteblower import HTTPMultiClientStatus_Finished
import time

# Minimal config parameters.

# Adapt to your setup.when necessary.
SERVER_ADDRESS = 'byteblower-tutorial-1300.lab.byteblower.excentis.com'

UDP_SRC_PORT = 9000
UDP_DEST_PORT = 1000

WAN_MAC = '00:BB:23:22:55:12'
WAN_BB_INTERFACE = 'nontrunk-1'

LAN_MAC = '00:BB:23:21:55:13'
LAN_BB_INTERFACE = 'trunk-1-45'

# Every session will download this many bytes
DOWNLOAD_SIZE = 512 * 1000

# Test duration, in seconds
TEST_DURATION = 2

# Number of sessions to run in parallel.
# Browsers usually do this.
PARALLEL_SESSIONS = 200


# ByteBlower part of the test.
api = byteblower.ByteBlower.InstanceGet()
server = api.ServerAdd(SERVER_ADDRESS)


def create_port(interface, mac_addr):
    port = server.PortCreate(interface)
    l2 = port.Layer2EthIISet()
    l2.AddressSet(mac_addr)

    l3 = port.Layer3IPv4Set()
    l3.ProtocolDhcpGet().Perform()
    return port


wan_port = create_port(WAN_BB_INTERFACE, WAN_MAC)
wan_ip = wan_port.Layer3IPv4Get().IpGet()

lan_port = create_port(LAN_BB_INTERFACE, LAN_MAC)
lan_ip = lan_port.Layer3IPv4Get().IpGet()

# setup a 'standard' HTTP web server
http_server = wan_port.ProtocolHttpMultiServerAdd()
http_server.PortSet(80)
http_server.Start()

# Configure our client
http_client = lan_port.ProtocolHttpMultiClientAdd()

http_client.LocalPortRangeSet(10000, 60000)
http_client.RemoteAddressSet(wan_ip)
http_client.RemotePortSet(http_server.PortGet())

http_client.DurationSet(TEST_DURATION * 1000000000)  # duration is in nanoseconds
http_client.MaximumConcurrentRequestsSet(PARALLEL_SESSIONS)
http_client.SessionSizeSet(DOWNLOAD_SIZE)

http_client.Start()

http_client_result = http_client.ResultGet()

while http_client.StatusGet() != HTTPMultiClientStatus_Finished:
    http_client_result.Refresh()
    print("Connections created:", http_client_result.ConnectionsAttemptedGet())
    time.sleep(.5)

failed_connections = http_client_result.ConnectionsAbortedGet() + http_client_result.ConnectionsRefusedGet()

print("Result:")
print("Average Transmit Speed: {}".format(http_client_result.TcpTxSpeedGet().toString()))
print("Average Receive speed:  {}".format(http_client_result.TcpRxSpeedGet().toString()))
print("Connections attempted:  {}".format(http_client_result.ConnectionsAttemptedGet()))
print("Connections passed:     {}".format(http_client_result.ConnectionsEstablishedGet()))
print("Connections failed:     {}".format(failed_connections))

# Cleanup the Server. The API will implicitly clean up
#  the create objects.
api.ServerRemove(server)
