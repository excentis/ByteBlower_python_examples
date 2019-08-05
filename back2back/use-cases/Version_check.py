#!/usr/bin/python
import byteblowerll.byteblower as byteblower
import requests
import time
import xml.etree.ElementTree as ET



def checkVersions(series, version):
    # url
    url = 'http://bbdl.excentis.com/server/update2.0/latest-versions.xml'
    # creating HTTP response object from given url
    resp = requests.get(url)
    # saving the xml file
    with open('versions.xml', 'wb') as f:
        f.write(resp.content)

    tree = ET.parse('versions.xml')
    root = tree.getroot()
    if root.find('./server[@series="{}"]'.format(series)).attrib['version'] == version:
        print("up to date")
    else:
        print("there is a newer version available")




try:
    bb = byteblower.ByteBlower.InstanceGet()
    bbServer = byteblower.ByteBlower.InstanceGet().ServerAdd("byteblower-tutorial-1300.lab.byteblower.excentis.com")

    version = bbServer.ServiceInfoGet().VersionGet()
    series = bbServer.ServiceInfoGet().SeriesGet()

    checkVersions(series, version)




except byteblower.DomainError as e:
    print "Caught DomainError: " + e.getMessage()

except byteblower.TechnicalError as e:
    print "Caught TechnicalError: " + e.getMessage()

except Exception as e:
    print(e.message)
