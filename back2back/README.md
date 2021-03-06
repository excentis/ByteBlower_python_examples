# ByteBlower port examples
These examples show how to configure traffic between two ByteBlower ports.

- ipv4.py

  Straightforward IPv4 frameblasting test.
  
  The speed can be configured using the frame interval (interframegap) or using
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

  Straightforward IPv6 frameblasting test.
  
- httpmulticlient.py

  Demonstrates how to use the HTTP MultiClient / MultiServer to setup multiple
  HTTP connections using only one HTTPMultiClient object.

- tcp.py

  Explains how to run statefull TCP between 2 ByteBlower ports.  IPv4 and IPv6 
  are covered.

