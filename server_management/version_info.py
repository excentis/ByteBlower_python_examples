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
    sys.exit(-1)

bb = byteblower.ByteBlower.InstanceGet()
server = bb.ServerAdd(SERVER_ADDRESS)
version_info = server.ServiceInfoGet().VersionGet()

print("ByteBlower Server: %s -- %s" % (SERVER_ADDRESS, version_info)) 

