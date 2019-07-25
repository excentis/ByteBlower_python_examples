# ByteBlower python examples

This repository contains all public available Python examples on how to use the ByteBlower Python API. 



## Folder structure
- back2back : examples between two ByteBlower ports.
- wireless_endpoint : Examples of using the Wireless Endpoint.
- server_management: No traffic is sent in these examples, they show how to get info from the ByteBlower Server and Meeting point.


## Dependencies
- ByteBlower Python API : http://setup.byteblower.com/software.html#API
- scapy: `pip install scapy`

    warning: when using scapy >2.4.0 on Windows 10: scapy cannot find NPCAP


## Loading and using the ByteBlower API
To load the ByteBlower API into python use following import statement
`from byteblowerll.byteblower import ByteBlower`



If you have requests, or missing an example, don't hesitate to ask us at support.byteblower@excentis.com
