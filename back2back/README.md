# ByteBlower port examples
These examples show how to configure traffic between two ByteBlower ports.

- eth_vlan_only.py

  Straightforward frame blasting test.  

  This test only requires ethernet II and optionally VLAN connectivity.  
  It demonstrates sending and receiving traffic with only Layer2 and optionally
  VLAN configuration.  A QinQ (nested VLANs) configuration is also supported.
  
- ipv4.py

  Straightforward IPv4 frame-blasting test.
  
  The speed can be configured using the frame interval ("interframegap") or using
  a given throughput in Megabits per second.  In the latter case, the frame 
  interval will be calculated.
 
- ipv4_multiflow.py

  Demonstrates the use of PortsStart and ResultsRefresh to start multiple ports
  at once and refresh multiple results at once.

- ipv4_latency.py

  Demonstrates the use of latency measurements with ByteBlower ports.  The 
  example is IPv4 only, but the IPv6 implementation is analogous.  Please 
  refer to the basic IPv6 examples for how to setup IPv6 streams and triggers.

- ipv4_outofsequence.py
  
  Demonstrates the use of out of sequence detections.  This example is IPv4 
  only, but IPv6 is analogous.  Please refer to IPv6 examples for IPv6 setup of
  streams and triggers.

- ipv6.py

  Straightforward IPv6 frame-blasting test.
  
- httpmulticlient.py

  Demonstrates how to use the HTTP MultiClient / MultiServer to setup multiple
  HTTP connections using only one HTTPMultiClient object.

- tcp.py

  Explains how to run stateful TCP between 2 ByteBlower ports.  IPv4 and IPv6 
  are covered.

- tcp_oneway_latency.py
  
  Demonstrates how the TCP OneWayLatency feature can be used.
  
  It collects the following data for a session:
  - total transmitted bytes
  - total received bytes
  - average throughput at the sending side
  - average throughput at the receiving side
  - the latency measurements for the data flowing from the sending side to the receiving side 
    (minimum, average, maximum, jitter)
  - The interval results for the session:
    - average throughput
    - latency measurements (minimum, average, maximum, jitter)
  
  