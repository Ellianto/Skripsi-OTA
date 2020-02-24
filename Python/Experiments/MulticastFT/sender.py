"""
    Credits to https://www.youtube.com/watch?v=AnJ9ULerxMg&t=8s

    Modifications inspired by Dennis Bush's UFTP
"""

import socket
import sys
import time

from pathlib import Path

import hashlib

"""
    1 MB File transfer time (in relation to buffer size):
    -> 1024 : 54.6 seconds
    -> 512  : 108.9 seconds
"""

# TODO: Adjust command codes to balance readiblity and buffer_size
"""
    Command Codes to send:
    a : Abort because some other devices failed
    c : Any device with the specified cluster ID should join
    d : The device with the specified device ID should join
    h : The following is the file hashsum
    s : Start the update process
    t : Begin file transfer process
"""

global_multicast_group = ('224.255.255.255', 5432)
data_multicast_group = ('227.0.0.1', 8888)
buffer_size = 1024 # TODO: Try to use a sensible number
file_path = Path('test_code.zip')
addr = []
command_timeout = 5
target_clients = ['target_device_001', 'non_existing_id']

def read_in_chunks(file_object, chunk_size=buffer_size):
    while True:
        chunk_data = file_object.read(chunk_size)
        if not chunk_data:
            break

        yield chunk_data

def getSize(file_object):
    file_object.seek(0, 2)
    size = file_object.tell()
    file_object.seek(0)
    return size

def md5CheckSum(file_path, blocksize=1024):
    hash = hashlib.md5()
    with file_path.open(mode='rb') as f:
        for block in iter(lambda: f.read(blocksize), b''):
            hash.update(block)
    return hash.hexdigest()

try:
    command_multicast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    data_multicast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    print('Multicast Sockets Created!')
except socket.error:
    print('Failed to create Multicast Sockets!')
    sys.exit()

command_multicast_socket.settimeout(float(command_timeout))

# TODO: Try use unicast UDP for target based update

try:
    # Advertise initialization message
    bytes = file_path.open(mode='rb')
    size = getSize(bytes)
    #! Format: [command_code]|[target_id]|[size]|[priv_addr:port]
    init_msg = 'c|target_cluster_x01|{}|{}'.format(
        str(size), ':'.join(map(str, data_multicast_group)))

    command_multicast_socket.sendto(str.encode(init_msg), global_multicast_group)

    clients_ok = False
    clients_replied = []
    response_time = []

    # Initialization Listen Phase
    while True:
        try:
            start = time.time()
            data, addr = command_multicast_socket.recvfrom(buffer_size)
            response_time.append(time.time() - start)
            print('Received {} from {}'.format(data, addr))
            client_reply = [val.decode() for val in data.split(b'|')]

            if client_reply[0] == 'OK':
                clients_replied.append(client_reply[1])
            elif client_reply[0] in ['NO', 'FA']:
                break
        except socket.timeout:
            print('No longer receiving response!')
            break
        except OSError:
            print('Specified Buffer Size is not enough!')
            sys.exit()
        else:
            if len(clients_replied) > len(target_clients):
                print("WHAT??")
                break

            if set(target_clients) == set(clients_replied):
                clients_ok = True
                break

    print('Response Time: ')
    print(response_time)
    print('Clients Responded: ')
    print(clients_replied)

    # Data transfer Phase
    if clients_ok is True:
        time.sleep(0.5) # Give some time to the last client to prepare data socket 
        command_multicast_socket.sendto(
            str.encode('t|target_cluster_x01'), global_multicast_group)

        for piece in read_in_chunks(bytes):
            data_multicast_socket.sendto(piece, data_multicast_group)
            time.sleep(0.05) # give some breathing room

        hashsum = md5CheckSum(file_path)
        print('File Checksum : ' + str(hashsum))
        print('Checksum length : ' + str(len(hashsum)))

        # Send hashsum for end devices integrity data check
        command_multicast_socket.sendto(
            str.encode('h|'+ hashsum), global_multicast_group)

        # Wait fot integrity check response (until timeout or all responded)
        clients_acked = []
        transfer_ok = False
        while True:
            try:
                data, addr = command_multicast_socket.recvfrom(buffer_size)
                print('Received {} from {}'.format(data, addr))
                client_reply = [val.decode() for val in data.split(b'|')]

                if client_reply[0] == 'ACK':
                    clients_acked.append(client_reply[1])
                elif client_reply[0] in ['NEQ']:
                    break
            except socket.timeout:
                print('Some clients failed to ACK')
                break
            except OSError:
                print('Specified Buffer Size is not enough!')
                sys.exit()
            else:
                if len(clients_acked) > len(clients_replied):
                    print("WHAT??")
                    break

                if set(clients_acked) == set(clients_replied):
                    transfer_ok = True
                    break

        print('Clients ACKed: ')
        print(clients_acked)

        if transfer_ok is True:
            cmd_msg = 's|target_cluster_x01'
        else:
            cmd_msg = 'a|target_cluster_x01'

        # Send command to start/abort the update
        command_multicast_socket.sendto(
            str.encode(cmd_msg), global_multicast_group)
    else:
        command_multicast_socket.sendto(
            str.encode('a|target_cluster_x01'), global_multicast_group)

        if len(clients_replied) == 0:
            print('No clients replied!')
        else:
            print('Some clients failed to connect!')

finally:
    print('Finishing Multicast File Transfer Session!')
    command_multicast_socket.close()
    data_multicast_socket.close()
