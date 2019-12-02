#!/usr/bin/python
from __future__ import print_function
import byteblowerll.byteblower as byteblower
import requests
import xml.etree.ElementTree as ET
import sys


class UpdateChecker(object):
    URL = 'http://bbdl.excentis.com/server/update2.0/latest-versions.xml'

    def __init__(self, server_address):
        self._server_address = server_address

    def get_server_info(self):
        bb = byteblower.ByteBlower.InstanceGet()
        bb_server = None

        try:
            bb_server = bb.ServerAdd(self._server_address)

            version = bb_server.ServiceInfoGet().VersionGet()
            series = bb_server.ServiceInfoGet().SeriesGet()

            return series, version

        finally:
            if bb_server is not None:
                bb.ServerRemove(bb_server)

    def update_available(self, series, version):

        # creating HTTP response object from given url
        resp = requests.get(self.URL)
        # saving the xml file
        with open('versions.xml', 'wb') as f:
            f.write(resp.content)

        tree = ET.parse('versions.xml')
        root = tree.getroot()
        return root.find('./server[@series="{}"]'.format(series)).attrib['version'] == version


if __name__ == '__main__':
    server_address = "byteblower-tutorial-1300.lab.byteblower.excentis.com"
    if len(sys.argv) == 2:
        server_address = sys.argv[1]

    version_checker = UpdateChecker(server_address)

    try:
        series, version = version_checker.get_server_info()

    except byteblower.DomainError as e:
        print("Caught DomainError: " + e.getMessage())
        sys.exit(1)

    except byteblower.TechnicalError as e:
        print("Caught TechnicalError: " + e.getMessage())
        sys.exit(1)

    try:
        update_available = version_checker.update_available(series, version)

    except Exception as e:
        print(str(e))
        sys.exit(1)

    if not update_available:
        print("up to date")
    else:
        print("there is a newer version available")
