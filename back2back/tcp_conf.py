#------------------------#
#   Test Configuration   #
#------------------------#

# --- ByteBlower Server address
serverAddress = "byteblower-dev-2100-3.lab.byteblower.excentis.com"

# --- Physical Ports to connect the logical ByteBlowerPorts to
physicalPort1 = "trunk-1-1"
physicalPort2 = "trunk-1-2"

# --- Layer2 Configuration
serverMacAddress = "00:ff:bb:ff:ee:dd"
clientMacAddress = "00:ff:bb:ff:ee:ee"

# --- Layer3 Configuration
# --- HTTP Server Port Layer3 Configuration
#   - Set to 1 if you want to use DHCP
serverPerformDhcp = False
#   - else use static IPv4 Configuration
serverIpAddress = "192.168.0.2"
serverNetmask = "255.255.255.0"
serverIpGW = "192.168.0.1"

# --- HTTP Client Port Layer3 Configuration
#   - Set to 1 if you want to use DHCP
clientPerformDhcp = False
#   - else use static IPv4 Configuration
clientIpAddress = "192.168.0.3"
clientNetmask = "255.255.255.0"
clientIpGW = "192.168.0.1"

# --- HTTP Session setup


# --- Number of bytes to request
requestSize = 1000000000 ;# 100 MB

# --- Configure the used HTTP Request Method
#
# - ByteBlower Server > version 1.4.8 and ByteBlower Client API > version 1.4.4
#   support configuring the used HTTP Method to transfer the data.
#   note: older versions always used HTTP GET
#
#   using HTTP GET :
#       HTTP Server -----D-A-T-A----> HTTP Client
#
#   using HTTP PUT :
#       HTTP Server <----D-A-T-A----- HTTP Client
#
httpMethod = "GET" ;# ByteBlower default
#httpMethod = "PUT"

#  - Uncomment this to set the initial TCP window size
#tcpInitialWindowSize 16384
#  - Uncomment this to enable TCP window scaling and set the window scale factor
#windowScale 4
