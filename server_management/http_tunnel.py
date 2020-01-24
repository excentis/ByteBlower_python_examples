"""
    You can use the ByteBlower API to access systems connected to 
    the traffic interfaces.

    As an example, with this script you can browse to the webpage
    of a modem connected to the ByteBlower Switch.

    All HTTP traffic between the your computer and the modem is
    tunneled over the ByteBlower API.
    
    To keep things easy, we've called this example an http_tunnel.
    as you'll notice when browsing through the code, there's nothing
    realling HTTP specific; the tunnel can be used for other 
    protocols also. E.g. set the remote port to 22 for SSH.
"""
import time
import signal 
import sys

import byteblowerll.byteblower as bb


## Configuration
BB_SERVER = 'byteblower-dev-4100-2.lab.byteblower.excentis.com'
BB_INTERFACE = 'trunk-1-11'

LOCAL_TCP_PORT  = 8080
REMOTE_TCP_PORT = 80
MODEM_IP_ADDR  = '192.168.0.200'


## Cleanup
def cleanup_on_signal(bb_api, bb_server)
    """
        Cleans up the ByteBlower Server when a signal is 
        invoked.
    """
    def cleanup(signum, frame):
        signal.signal(signum, signal.default_int_handler)
        api.ServerRemove(server)
        sys.exit(0)

    interested_signals = ['SIGABRT', 'SIGTERM', 
                     'SIGINT', 'CTRL_C_EVENT']
    for a_signal in interested_signals:
            if hasattr(signal, a_signal):
                signal_code = getattr(signal, a_signal)
                signal.signal(signal_code, cleanup)

# actual Code 
api = bb.ByteBlower.InstanceGet()
server = api.ServerAdd(BB_SERVER)
cleanup_on_signal(api, server)

port = server.PortCreate(BB_INTERFACE)

l2 = port.Layer2EthIISet()
l2.MacSet('00-bb-ff-01-02-13')

l3 = port.Layer3IPv4Set()
l3.IpSet('192.168.0.11')
l3.GatewaySet('192.168.0.1')
l3.NetmaskSet('255.255.255.0')

tunnel = port.TunnelTcpAdd()
tunnel.LocalPortSet(LOCAL_TCP_PORT)
tunnel.RemoteAddressSet(MODEM_IP_ADDR)
tunnel.RemotePortSet(REMOTE_TCP_PORT)

tunnel.Start()
print('Tunnel active from %s:%d to %s:%d' % 
        ('localhost', LOCAL_TCP_PORT, 
         MODEM_IP_ADDR, REMOTE_TCP_PORT))

print('Press ctrl+c to stop the tunnel')

while True:
    time.sleep(1)

