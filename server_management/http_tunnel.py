"""
    You can use the ByteBlower API to access systems connected to 
    the traffic interfaces.

    As an example, with this script you can browse to the webpage
    of a modem connected to the ByteBlower Switch.

    All HTTP traffic between the your computer and the modem is
    tunneld over the ByteBlower API.
"""
import time
import signal 
import sys

import byteblowerll.byteblower as bb

BB_SERVER = 'byteblower-dev-4100-2.lab.byteblower.excentis.com'
BB_INTERFACE = 'trunk-1-11'

LOCAL_TCP_PORT  = 8080
REMOTE_TCP_PORT = 80
MODEM_IP_ADDR  = '192.168.0.200'

api = bb.ByteBlower.InstanceGet()
server = api.ServerAdd(BB_SERVER)

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

port = server.PortCreate(BB_INTERFACE)

l2 = port.Layer2EthIISet()
l2.MacSet('00-bb-ff-01-02-13')

l3 = port.Layer3IPv4Set()
l3.IpSet('192.168.0.11')
l3.GatewaySet('192.168.0.1')
l3.NetmaskSet('255.255.255.0')


icmp = l3.ProtocolIcmpGet()
ping_session = icmp.SessionAdd()
ping_session.RemoteAddressSet(MODEM_IP_ADDR)
ping_session.EchoLoopIntervalSet(10 ** 9)
ping_session.EchoLoopStart()
for _ in range(5):
    time.sleep(1.1)
    ping_session.Refresh()
    print(ping_session.SessionInfoGet().DescriptionGet())

tunnel = port.TunnelTcpAdd()
tunnel.LocalPortSet(LOCAL_TCP_PORT)

tunnel.RemoteAddressSet(MODEM_IP_ADDR)
tunnel.RemotePortSet(REMOTE_TCP_PORT)

tunnel.Start()
print('Tunnel active from %s:%d to %s:%d' % 
        ('localhost', LOCAL_TCP_PORT, 
         MODEM_IP_ADDR, REMOTE_TCP_PORT))
while True:
    time.sleep(1)
api.ServerRemove(server)
