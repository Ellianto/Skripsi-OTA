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

multicast_addr = '224.255.255.255' # Address and port have to match sender side
server_address = ('', 5432) # empty string = bind to all interface

# Creates the socket
udp_receiver = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Binds the Server Address
# By default, sockets are created in 'blocking' mode
udp_receiver.bind(server_address)

# Tell the OS to add socket to multicast group
# Since server_address implies '', then on all interfaces

# Piece of code to send "Membership Report/Join Group" IGMPv3 packet
# converts IPv4 octet string into bytes
group = socket.inet_aton(multicast_addr)
mreq = struct.pack('=4sL', group, socket.INADDR_ANY) #INADDR_ANY means to listen to all interface
# Sets the Socket Option
udp_receiver.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

"""
    =4sL is struct.pack() specific used for specifying the byte format
    =4sL means:
    '=' : use platform endianness (native byte order, standard size, no alignment)
    '4s': The first thing is a string of 4 char joined into a bytestring
    'L' : followed by a signed long int (4 byte)
"""

# Receive/Respond Loop
while True:
    print('\nWaiting to receive message...')
    # First param is buffer size
    """
        For best match with hardware and network realities, the value of 
        bufsize should be a relatively small power of 2, for example, 4096.
    """
    # socket.recvfrom(bufsize) returns (nbytes, address)
    # nbytes = numebr of bytes received
    # address = string of address where the data came from
    # blocks process until a data is received
    data, address = udp_receiver.recvfrom(1024)

    print('Received {} bytes from {}'.format(len(data), address))
    print(data)

    print('Sending ACK to ', address)

    # Sending byte data to specified address
    # data length matters! Make sure the length is < buffer size in the other side
    udp_receiver.sendto(b'such_a_long_string_to_be_placed_specifically_in_this_position', address)
