"""
    Lists all API users on a ByteBlower Server

    This script needs a single argument to run:
        The ByteBlower server you'd like to get info from.

    As example:
     > python bb_users.py byteblower-tutorial-1300.lab.byteblower.excentis.com
     
    
    This example will print out the folowing list
        # Interface name, user_name
        nontrunk-1, 'pieter.v@laptop-019'
        trunk-1-45, 'pieter.v@laptop-019'
        trunk-1-15, 'excentis@laptop-030'
        trunk-1-45, 'excentis@laptop-030'


    

"""    

import byteblowerll.byteblower as byteblower
import sys

if len(sys.argv) == 2:
    SERVER_ADDRESS = sys.argv[1]
else:
    print("Expected arguments: %s <ByteBlower-server>" % sys.argv[0])
    sys.exit(-1)

bb = byteblower.ByteBlower.InstanceGet()

server = bb.ServerAdd(SERVER_ADDRESS)

print('')

print("# Interface name, user_name")
for u in server.UsersGet():
    if_name = u.InterfaceGet().NameGet()
    user_name = u.NameGet()
    desc = "%s, '%s'" % (if_name, user_name)
    print(desc)
