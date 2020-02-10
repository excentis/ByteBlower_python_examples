"""
    Prints out the version of the ByteBlower API.
    
    Running this script is an easy check wether 
    everything is installed properly.
"""
from __future__ import print_function
import byteblowerll.byteblower as byteblower

try:
    instance = byteblower.ByteBlower.InstanceGet()
    print("ByteBlower API version: " + instance.APIVersionGet())

except Exception as e:
    print("Caught Exception: " + str(e))
