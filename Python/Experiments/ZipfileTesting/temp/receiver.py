"""
    Credits to https://www.youtube.com/watch?v=AnJ9ULerxMg&t=8s

    Modifications inspired by Dennis Bush's UFTP
"""

import socket
import sys
import time
import hashlib
import struct
import zipfile

import psutil

from pathlib import Path

curr_dir = Path(__file__).parent.absolute()
data_dir = curr_dir / 'data'
target_file = data_dir / 'target.zip'


"""
    Reply Codes to send:
    -> Main Phase:
        OK : Ready for file transfer (sufficient free space)
        FA : Failed somehow (find use for this)
        NO : Not enough disk space

    -> End Phase:
        ACK : Files received successfully (hashsum matches)
        NEQ : Files hashsum doesn't match
"""

# ! Buffer size in client side must be larger than packet sent gateway-side
command_multicast_addr = socket.inet_aton('224.255.255.255')
global_multicast_group = ('', 5432)
data_multicast_group = None
buffer_size = 1024  # TODO: Try to use a more fitting number

device_id = 'target_device_001'
cluster_id = 'target_cluster_x01'

def md5CheckSum(file_path, blocksize=1024):
    hash = hashlib.md5()
    with file_path.open(mode='rb') as f:
        for block in iter(lambda: f.read(blocksize), b''):
            hash.update(block)
    return hash.hexdigest()

try:
    global_multicast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    global_multicast_socket.bind(global_multicast_group)
    print('Global Multicast Socket Created successfully!')
except socket.error:
    print('Failed to create Global Multicast Socket!')
    sys.exit()
    

try:
    mreq = struct.pack('=4sL', command_multicast_addr, socket.INADDR_ANY)
    global_multicast_socket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    print('Successfully registered to Command Multicast Address Group!')
except socket.error:
    print('Failed to join to Command Multicast Group!')
    sys.exit()

while True:
    try:
        print('Waiting for server...')
        global_multicast_socket.settimeout(None)
        msg, addr = global_multicast_socket.recvfrom(buffer_size)
        messages = [val.decode() for val in msg.split(b'|')]

        if messages[0] in ['c', 'd']:
            should_listen = (device_id if messages[0] == 'd' else cluster_id) == messages[1]
        else:
            raise ValueError

        if should_listen is True:
            # Check if filesize will fit properly
            free_space = psutil.disk_usage(str(curr_dir)).free
            file_size = int(messages[2])

            if float(free_space * 0.95) > float(file_size):
                global_multicast_socket.sendto(str('OK|' + device_id).encode(), addr)
                print('File Size : ' + str(file_size) + ' bytes')
                [data_multicast_addr, data_multicast_port] = messages[3].split(':')

                try:
                    data_multicast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    data_multicast_socket.bind(('', int(data_multicast_port)))
                    print('Data Multicast Socket Created successfully!')
                except socket.error:
                    print('Failed to create Data Multicast Socket!')
                    sys.exit()

                try:
                    data_mreq = struct.pack('=4sL', socket.inet_aton(data_multicast_addr), socket.INADDR_ANY)
                    data_multicast_socket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, data_mreq)
                    print('Successfully registered to Data Multicast Address Group!')
                except socket.error:
                    print('Failed to join to Data Multicast Group!')
                    sys.exit()

                transfer_cmd, addr = global_multicast_socket.recvfrom(buffer_size)
                transfer_msg = [val.decode() for val in transfer_cmd.split(b'|')]

                if transfer_msg[0] == 't':
                    with target_file.open(mode='wb') as file:
                        total = 0
                        start = time.time()
                        while total < file_size:
                            file_data, incoming_addr = data_multicast_socket.recvfrom(
                                buffer_size)
                            file.write(file_data)
                            total += len(file_data)
                            print('Current Size Received : ' + str(total))
                            print('Progress : {}%'.format(
                                str((total/file_size) * 100)))

                        print('File received completely! Closing data socket...')
                        print('Time Elapsed : ' + str(time.time() - start))
                        data_multicast_socket.close()

                    server_checksum = None
                    try:
                        global_multicast_socket.settimeout(3.0)
                        ack_cmd, addr = global_multicast_socket.recvfrom(
                            buffer_size)
                        ack_msg = [val.decode() for val in ack_cmd.split(b'|')]
                        server_checksum = ack_msg[1] if ack_msg[0] in [
                            'h'] else None

                        hashsum = md5CheckSum(target_file)
                        print('File Checksum : ' + str(hashsum))
                        print('Checksum length : ' + str(len(hashsum)))

                        ack_reply = 'NEQ|' + device_id

                        if server_checksum == hashsum:
                            ack_reply = 'ACK|' + device_id
                            if zipfile.is_zipfile(str(target_file)) is True:
                                # TODO: Handle bad zip files?
                                pass
                            else:
                                raise zipfile.BadZipFile
                        else:
                            print('File Hashsum mismatch!')

                        # Send ACK or NEQ (Hashsum not equal message)
                        global_multicast_socket.sendto(ack_reply.encode(), addr)

                        # Wait for go (g|xxx), abort (a|xxx) or timeout
                        global_multicast_socket.settimeout(5.0)
                        start_cmd, addr = global_multicast_socket.recvfrom(
                            buffer_size)
                        start_msg = [val.decode() for val in start_cmd.split(b'|')]

                        if start_msg[0] == 's':
                            with zipfile.ZipFile(str(target_file)) as new_zip:
                                new_zip.extractall(path=data_dir)
                        elif start_msg[0] == 'a':
                            if target_file.exists() is True:
                                target_file.unlink()

                    except socket.timeout:
                        print('No ACK from server!')
                    except zipfile.BadZipFile:
                        print('Bad Zip File Received!')                
            else:
                print('File cannot fit into memory!')
                print('It is advised to leave at least 5% of free disk space')
    except ValueError:
        print('Invalid Message Format!')
        print(msg)
    finally:
        data_multicast_group = None
        if target_file.exists() is True:
            target_file.unlink()



