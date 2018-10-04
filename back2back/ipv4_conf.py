# This configuration file initializes the necessary variables to run the IPv4.run.tcl back2back example.
# We need to configure the server, ports, mac and ip addresses, as well as traffic parameters.

#------------------------#
#   Test Configuration   #
#------------------------#

# --- ByteBlower Server address
serverAddress = "byteblower-dev-2100-3.lab.byteblower.excentis.com"

# --- Physical Ports to connect the logical ByteBlowerPorts to
physicalPort1 = "trunk-1-1"
physicalPort2 = "trunk-1-2"

# --- Layer2 Configuration
srcMacAddress1 = "00:FF:12:00:00:01"
dstMacAddress1 = "00:FF:12:00:00:02"

# --- Layer3 Configuration
# --- Back-To-Back Source Port Layer3 Configuration
#   - Set to 1 if you want to use DHCP
srcPerformDhcp1 = False
#   - else use static IPv4 Configuration
srcIpAddress1 = "10.10.0.2"
srcNetmask1 = "255.255.255.0"
srcIpGW1 = "10.10.0.1"

# --- Back-To-Back Destination Port Layer3 Configuration
#   - Set to 1 if you want to use DHCP
dstPerformDhcp1 = False
#   - else use static IPv4 Configuration
dstIpAddress1 = "10.10.0.3"
dstNetmask1 = "255.255.255.0"
dstIpGW1 = "10.10.0.1"

# ---- Frame configuration
ethernetLength = 124 ;# without CRC!


# --- UDP Configuration
srcUdpPort1 = 2001
dstUdpPort1 = 2002

# --- Timing configuration
#   - Number of frames to send
numberOfFrames = 10000
#   - Time between two frames (ns)
interFrameGap = 1000000

# ---- Traffic direction configuration
# set to 1 for bidirectional traffic
bidir = True
