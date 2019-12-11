"""
    Shows which version the ByteBlower Server runs. 
    It requires the ByteBlower server address as argument.

    As example:
     > python version_info.py byteblower-tutorial-1300.lab.byteblower.excentis.com

    This prints out following:
         ByteBlower Server: byteblower-tutorial-1300.lab.byteblower.excentis.com -- 2.10.2
"""    


import byteblowerll.byteblower as byteblower
import sys

if len(sys.argv) == 2:
    SERVER_ADDRESS = sys.argv[1]
else:
    print("Expected argument: %s <ByteBlower-server>" % sys.argv[0])
    sys.exit(1)

# Initialize the ByteBlower API.
bb = byteblower.ByteBlower.InstanceGet()
server = None

try:
    # Connect to the ByteBlower server
    server = bb.ServerAdd(SERVER_ADDRESS)

    # Get the version.  It is in the format "Major.Minor.Patch"
    version_info = server.ServiceInfoGet().VersionGet()

    print("ByteBlower Server: %s -- %s" % (SERVER_ADDRESS, version_info))

except (byteblower.DomainError, byteblower.TechnicalError):
    print("Could not connect to the server")

finally:
    # If we are connected to a server, disconnect from it.
    # This is considered good practise since all resources are released.
    if server is not None:
        bb.ServerRemove(server)
