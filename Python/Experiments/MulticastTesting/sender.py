"""
    Based on the example taken from https://pymotw.com/3/socket/multicast.html

    Also, refer to these:
    https://docs.python.org/3/library/socket.html
    http://www.tldp.org/HOWTO/Multicast-HOWTO-6.html
    https://stackoverflow.com/questions/16419794/what-is-4sl-format-in-struct-pack-python
"""

import socket
import struct
import sys
import time

# Address and port have to match receiver side
multicast_group = ('224.100.100.100', 10000)

# Create the Datagram socket by specifying SOCK_DGRAM
udp_sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Set Socket to Timeout mode and specify timeout value
# So the socket doesn't block the program while waiting for data
udp_sender.settimeout(0.2)

# Setting the TTL Value of multicast packets
ttl = struct.pack('b', 1)
udp_sender.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)

try:
    # Sending data to multicast group
    payload = b'sum_data'
    print('Sending {}'.format(payload))
    return_code = udp_sender.sendto(payload, multicast_group)

    # Wait for responses from recipients in the specified Multicast Address
    default_buffer_size = 64

    while True:
        print('Waiting to receive (current buffer size: ' + str(default_buffer_size) + ' bytes)')
        try:
            start = time.time()
            # If timedout while waiting to receive, will raise socket.timeout Exception
            # BUFFER SIZES MATTERS, if data_send > buffer_size will raise OSError
            data, server = udp_sender.recvfrom(default_buffer_size)
        except socket.timeout:
            # Timeout value is based on the value passed to socket.settimeout(timeout_value)
            print('Timed out! No more response received')
            break
        except OSError:
            default_buffer_size *= 2
        else:
            print('Received {} from {}'.format(data, server))
        finally:
            # For time measurements, try to match with the timeout set in settimeout
            print(str(time.time() - start) + ' s elapsed!')

finally:
    print('Closing socket...')
    udp_sender.close()
