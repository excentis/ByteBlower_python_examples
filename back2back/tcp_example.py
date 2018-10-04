'''
Basic IPv4 Example for the ByteBlower Python API.
All examples are garanteed to work with Python 2.7 and above

Copyright 2016, Excentis N.V.
'''
## Needed for python2 / python3 print function compatibility
from __future__ import print_function

# import the ByteBlower module
import byteblowerll.byteblower as byteblower

# import the configuration for this example
from tcp_conf import *

from example_generic import create_port

import time

def run():
    
    byteblower_instance = byteblower.ByteBlower.InstanceGet()
    
    print("Connecting to ByteBlower server {}...".format(serverAddress))
    server = byteblower_instance.ServerAdd(serverAddress)
    
    httpServerPort = create_port(server, physicalPort1, serverMacAddress, "ipv4", serverPerformDhcp, serverIpAddress, serverNetmask, serverIpGW)
    
    httpClientPort = create_port(server, physicalPort2, clientMacAddress, "ipv4", clientPerformDhcp, clientIpAddress, clientNetmask, clientIpGW)
    
    print("Server port:", httpServerPort.DescriptionGet())
    print("Client port:", httpClientPort.DescriptionGet())
    
    actualServerIpAddress = httpServerPort.Layer3IPv4Get().IpGet()
    
    # create a HTTP server
    httpServer = httpServerPort.ProtocolHttpServerAdd()
    serverTcpPort = httpServer.PortGet()
    
    # create a HTTP Client
    httpClient = httpClientPort.ProtocolHttpClientAdd()
    
    # - remote endpoint
    httpClient.RemoteAddressSet(actualServerIpAddress)
    httpClient.RemotePortSet(serverTcpPort)
    
    httpClient.HttpMethodSet(httpMethod)

    
    print("Server port:", httpServerPort.DescriptionGet())
    print("Client port:", httpClientPort.DescriptionGet())
    
    
    # let the HTTP server listen for requests
    httpServer.Start()

    # let the HTTP Client request a page of a specific size...
    httpClient.RequestSizeSet(requestSize)    
    httpClient.RequestStart()
    
    # Wait until the HTTP Client is connected with the HTTP server for a 
    # maximum of 2 seconds
    httpClient.WaitUntilConnected(2 * 1000000000)
    
    # Wait until the HTTP Client has finished the "download"
    httpClient.WaitUntilFinished(60 * 1000000000)
    
    httpClient.RequestStop()
    httpServer.Stop()
    
    httpClientSessionInfo = httpClient.HttpSessionInfoGet()
    httpClientSessionInfo.Refresh()
    print("HTTP Client's Session Information:", httpClientSessionInfo.DescriptionGet())
    
    statusValue = httpClient.RequestStatusGet()
    
    txBytes = 0
    rxBytes = 0
    avgThroughput = 0
    minCongestion = 0
    maxCongestion = 0
    ##print("HTTPMethod:", byteblower.ConvertHTTPRequestMethodToString(httpClientSessionInfo.RequestMethodGet()))
    if httpClientSessionInfo.RequestMethodGet() == byteblower.HTTPRequestMethod_Get:
        httpSessionInfo = httpClient.HttpSessionInfoGet()
        httpResult = httpSessionInfo.ResultGet()
        httpResult.Refresh()
        
        txBytes = httpResult.TxByteCountTotalGet()
        rxBytes = httpResult.RxByteCountTotalGet()
        avgThroughput = httpResult.AverageDataSpeedGet()
        
        tcpResult = httpSessionInfo.TcpSessionInfoGet().ResultGet()
        tcpResult.Refresh()
        
        minCongestion = tcpResult.CongestionWindowMinimumGet()
        maxCongestion = tcpResult.CongestionWindowMaximumGet()
        
    elif httpClientSessionInfo.RequestMethodGet() == byteblower.HTTPRequestMethod_Get:
        httpSessionInfo = httpServer.HttpSessionInfoGet(httpClient.ServerClientIdGet())
        httpResult = httpSessionInfo.ResultGet()
        httpResult.Refresh()
        
        txBytes = httpResult.TxByteCountTotalGet()
        rxBytes = httpResult.RxByteCountTotalGet()
        avgThroughput = httpResult.AverageDataSpeedGet()
        
        tcpResult = httpSessionInfo.TcpSessionInfoGet().ResultGet()
        tcpResult.Refresh()
        
        minCongestion = tcpResult.CongestionWindowMinimumGet()
        maxCongestion = tcpResult.CongestionWindowMaximumGet()
       
    print("Requested Payload Size: {} bytes".format(requestSize))
    print("TX Payload            : {} bytes".format(txBytes))
    print("RX Payload            : {} bytes".format(rxBytes))
    print("Average Throughput    : {}".format(avgThroughput.toString()))
    print("Min Congestion Window : {} bytes".format(minCongestion))
    print("Max Congestion Window : {} bytes".format(maxCongestion))
    print("Status                : {}".format(byteblower.ConvertHTTPRequestStatusToString(statusValue)))
    
    return [requestSize, txBytes, rxBytes, avgThroughput, minCongestion, maxCongestion, statusValue ]
    
    
    
    
    
    

# When this python module is called stand-alone, the run-function must be
# called.  This approach makes it possible to include it in a series of
# examples.
if __name__ == "__main__":
    result = run()
    
