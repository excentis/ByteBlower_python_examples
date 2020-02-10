"""
With this script you can tunnel TCP traffic through a ByteBlower port.
E.g. connect to the webpage of your access-point through your trunk-1-1 port that's attached to that access-point

"""

from byteblowerll.byteblower import ByteBlower
import time


### CONFIGURATION PARAMETERS 

BYTEBLOWER = "byteblower-sales-1300.office.excentis.com"
BYTEBLOWER_PORT = "trunk-1-13"

REMOTE_ADDRESS = "192.168.11.36"
REMOTE_PORT = 22
LOCAL_PORT = 8080


### SCRIPT 

bb = ByteBlower.InstanceGet();

# Connect to the ByteBlower
server = bb.ServerAdd(BYTEBLOWER);

# Create your port
port1 = server.PortCreate(BYTEBLOWER_PORT);

# Configure the port with mac-address and perform DHCP
port1.Layer2EthIISet().AddressSet("00ff1c000001");
port1.Layer3IPv4Set().ProtocolDhcpGet().Perform();

# Create the TCP tunnel
tunnel = port1.TunnelTcpAdd()

# Configure the TCP tunnel
tunnel.RemoteAddressSet(REMOTE_ADDRESS)
tunnel.RemotePortSet(REMOTE_PORT)
tunnel.LocalPortSet(LOCAL_PORT)

# Start the TCP tunnel
tunnel.Start()

print("Tunnel activated on %s, to destination %s:%d" % (BYTEBLOWER,REMOTE_ADDRESS,REMOTE_PORT))
print("Point your browser to http://localhost:%s" % LOCAL_PORT) 
print("Ctrl + C to stop the tunnel")

while True:
    time.sleep(1)
