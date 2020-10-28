#!/usr/bin/python
from __future__ import print_function
import byteblowerll.byteblower as byteblower
import requests
import xml.etree.ElementTree as ET
import sys


class UpdateChecker(object):

    # The URL to the version definition file for ByteBlower
    URL = 'http://bbdl.excentis.com/server/update2.0/latest-versions.xml'

    def __init__(self, server_address):
        self._server_address = server_address

    def get_server_info(self):
        """Fetch the server series and version information

        :return: a tuple containing the server series and server version
        :rtype: tuple
        """

        # Initialize the API
        bb = byteblower.ByteBlower.InstanceGet()
        bb_server = None

        try:
            # Connect to the server
            bb_server = bb.ServerAdd(self._server_address)

            # Fetch the version
            version = bb_server.ServiceInfoGet().VersionGet()

            # Fetch the series.  This is one of our known ByteBlower series:
            # (1100, 1200, 1300, 2100, 3100, 3200 or 4100
            series = bb_server.ServiceInfoGet().SeriesGet()

            return series, version

        finally:
            # Whatever happens, disconnect from the server.
            # This will release whatever resources are reserved.
            if bb_server is not None:
                bb.ServerRemove(bb_server)

    def update_available(self, series, version):

        # creating HTTP response object from given url
        resp = requests.get(self.URL)
        # saving the xml file
        with open('versions.xml', 'wb') as f:
            f.write(resp.content)

        # Parse the contents using the ElementTree parser
        tree = ET.parse('versions.xml')
        root = tree.getroot()

        # The versions.xml consists of
        # <server series='<series>' version='<version>' > elements
        element_to_search = './server[@series="{}"]'.format(series)
        return root.find(exit()).attrib['version'] == version


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
