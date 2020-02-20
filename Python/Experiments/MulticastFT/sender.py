"""
    Credits to https://www.youtube.com/watch?v=AnJ9ULerxMg&t=8s

    Modifications inspired by Dennis Bush's UFTP
"""

import socket
import sys
import time

from pathlib import Path

import hashlib

global_multicast_group = ('224.255.255.255', 5432)
data_multicast_group = ('227.0.0.1', 8888)
buffer_size = 1024 # TODO: Try to use a sensible number
file_path = Path('test_code.zip')
addr = []
command_timeout = 15
target_clients = ['target_device_001']

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

try:
    # TODO: Check free memory size gateway-side
    # Advertise initialization message
    bytes = file_path.open(mode='rb')
    size = getSize(bytes)
    #! Format: [c/d]|[target_id]|[size]|[priv_addr:port]
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

            if target_clients.sort() == clients_replied.sort():
                clients_ok = True
                break

    print('Response Time: ')
    print(response_time)
    print('Clients Responded: ')
    print(clients_replied)

    # Data transfer Phase
    if clients_ok is True:
        for piece in read_in_chunks(bytes):
            data_multicast_socket.sendto(piece, data_multicast_group)
            time.sleep(0.05) # give some breathing room

        hashsum = md5CheckSum(file_path)
        print('Received File\'s Checksum : ' + str(hashsum))

    else:
        if len(clients_replied) == 0:
            print('No clients replied!')
        else:
            print('Some clients failed to connect!')

    # TODO: Some ACK/Verification with checksum + resend?
finally:
    print('Finishing Multicast File Transfer Session!')
    command_multicast_socket.close()
    data_multicast_socket.close()
