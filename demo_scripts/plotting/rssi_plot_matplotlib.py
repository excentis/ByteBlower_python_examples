#!/usr/bin/python
# def plot_data(device_name, data):
#     """
#     Plots the data collected by the example using matplotlib
#     :param device_name: Name of the device
#     :param data: The data returned by the example
#     """
#
#     timestamps = []
#     rssis = []
#     losses = []
#     throughputs = []
#
#     # Reformat the example data for use in the graphics
#     for item in data:
#         timestamps.append(item['timestamp'] / 1000000000)
#         losses.append(int(item['loss']))
#         throughputs.append(int(item['throughput'])/1000000.0)
#         rssis.append(item['rssi'])
#
#     # Reformat the timestamps so we have timestamps since the start of
#     # the example
#     min_ts = min(timestamps)
#     x_labels = [x - min_ts for x in timestamps]
#
#     # Get the default figure and axis
#     fig, axes = plt.subplots(2, 1)
#
#     ax1 = axes[0]
#
#     # Set the title of the graph
#     ax1.set_title(device_name + " UDP loss vs RSSI over time")
#
#     # Plot the throughput on the default axis, in the color red
#     ax1.plot(x_labels, losses, 'r')
#     ax1.set_ylabel('Loss (%)', color="red")
#     ax1.set_ylim(0, 100)
#     ax1.set_xlabel('Time')
#
#     # Add another Y axis, which uses the same X axis
#     ax2 = ax1.twinx()
#
#     # Plot the RSSI on the new axis, color is blue
#     ax2.plot(x_labels, rssis, 'b')
#     ax2.set_ylabel('RSSI (dBm)', color="blue")
#     ax2.set_ylim(-127, 0)
#
#     ax_throughput = axes[1]
#     # Set the title of the graph
#     ax_throughput.set_title(device_name + " UDP Throughput vs RSSI over time")
#
#     # Plot the throughput on the default axis, in the color red
#     ax_throughput.plot(x_labels, throughputs, 'r')
#     ax_throughput.set_ylabel('Throughput (Mbps)', color="red")
#     ax_throughput.set_ylim(bottom=0)
#     ax_throughput.set_xlabel('Time')
#
#     # Add another Y axis, which uses the same X axis
#     ax_throughput_rssi = ax_throughput.twinx()
#
#     # Plot the RSSI on the new axis, color is blue
#     ax_throughput_rssi.plot(x_labels, rssis, 'b')
#     ax_throughput_rssi.set_ylabel('RSSI (dBm)', color="blue")
#     ax_throughput_rssi.set_ylim(-127, 0)
#
#     # Crop the image
#     fig.tight_layout()
#     # Save the image
#     fig.savefig(os.path.basename(__file__) + ".png")
