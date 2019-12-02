#!/usr/bin/python
from __future__ import print_function
import byteblowerll.byteblower as byteblower
import sys


if __name__ == '__main__':
    server_address = "byteblower-tutorial-1300.lab.byteblower.excentis.com"
    server = None
    meetingpoint = None

    if len(sys.argv) == 2:
        server_address = sys.argv[1]

    bb = byteblower.ByteBlower.InstanceGet()

    try:
        server = bb.ServerAdd(server_address)
        meetingPoint = bb.MeetingPointAdd(server_address)

        print("server users: ")
        for user in server.UsersGet():
            print(user.NameGet())

        print("meeting point users: ")
        for user in meetingPoint.UsersGet():
            print(user.NameGet())

    except byteblower.DomainError as e:
        print("Caught DomainError: " + e.getMessage())

    except byteblower.TechnicalError as e:
        print("Caught TechnicalError: " + e.getMessage())

    except Exception as e:
        print(e.message)

    finally:
        if server is not None:
            bb.ServerRemove(server)

        if meetingpoint is not None:
            bb.MeetingPointRemove(meetingpoint)
