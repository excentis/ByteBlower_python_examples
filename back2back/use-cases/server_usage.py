#!/usr/bin/python
import byteblowerll.byteblower as byteblower
import sys


try:
    bb = byteblower.ByteBlower.InstanceGet()
    bbServer = byteblower.ByteBlower.InstanceGet().ServerAdd(sys.argv[1])
    meetingPoint = bb.MeetingPointAdd("byteblower-tutorial-1300.lab.byteblower.excentis.com")

    print("server users: ")
    for user in bbServer.UsersGet():
        print(user.NameGet())

    print("meeting point users: ")
    for user in meetingPoint.UsersGet():
        print(user.NameGet())






except byteblower.DomainError as e:
    print "Caught DomainError: " + e.getMessage()

except byteblower.TechnicalError as e:
    print "Caught TechnicalError: " + e.getMessage()

except Exception as e:
    print(e.message)
