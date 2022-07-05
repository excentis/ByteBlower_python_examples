"""
  This script exports information of the ByteBlower server 
  over openmetrics.
  
  This info can be used for scraping by Prometheus (TCP port 8200)
  
  This script expects the ByteBlower server as address.
"""
from prometheus_client import start_http_server, Counter, Gauge 
import random
import time
import sys

from byteblowerll import byteblower
OPENMETRICS_PORT=8200
REFRESH_PERIOD= 2 #Every 2 seconds

class ServerMetrics:
  SERVER_USERS = Gauge("byteblower_server_api_users", "API users connected to the ByteBlower Server", 
                        ["address", "interface"])

  SERVER_TRAFFIC = Counter("byteblower_server_interface_counter", "Counts the amount of received Bytes on the Traffic Interface", 
                        ["address", "interface"])

  def __init__(self, server_addr):
    self.server_addr = server_addr

    api = byteblower.ByteBlower.InstanceGet()
    self.server = api.ServerAdd(server_addr)

    self.port_counters = {}
    for interface_name in self.server.InterfaceNamesGet():
      port = self.server.PortCreate(interface_name)
      count_everything = port.RxTriggerBasicAdd()
      self.port_counters[interface_name] = {"ctr": count_everything, "prev_bytes": 0}

  def user_count(self):
      by_interface = {}
      for u in self.server.UsersGet():
        interface_name = u.InterfaceGet().NameGet()
        if interface_name in by_interface:
          by_interface[interface_name] += 1
        else:
          by_interface[interface_name] = 1
      for interface_name, count in by_interface.items():
        ServerMetrics.SERVER_USERS.labels(self.server_addr, interface_name).set(count)


  def traffic_count(self):
    for interface_name, traffic_info in self.port_counters.items():
      prev_bytes= traffic_info["prev_bytes"]
      ctr = traffic_info["ctr"]

      ctr.Refresh()
      current_bytes = ctr.ResultGet().ByteCountGet()
      ServerMetrics.SERVER_TRAFFIC.labels(self.server_addr, interface_name).inc(current_bytes - prev_bytes)
      traffic_info[prev_bytes] = current_bytes


if __name__ == '__main__':
  if len(sys.argv) < 2:
    print(f"{sys.argv[0]} expects 1 argument: the address of the ByteBlower Server")
    sys.exit(-1)

  SERVER_ADDR = sys.argv[1]
  start_http_server(OPENMETRICS_PORT)

  metrics = ServerMetrics(SERVER_ADDR)
  while True:
    time.sleep(REFRESH_PERIOD)
    metrics.user_count()
    metrics.traffic_count()


