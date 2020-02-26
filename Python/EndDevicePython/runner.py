import hashlib
import json
import socket as sock
import struct
import sys
import time
import zipfile

from pathlib import Path
from shutil import rmtree as recursive_rmdir
from signal import SIGTERM

import psutil

import constants
import requests


# File Handling Section
def md5Checksum(block_size):
    hash = hashlib.md5()
    with constants.paths.TEMP_DATA_FILE.open(mode='rb') as f:
        for block in iter(lambda: f.read(block_size), b''):
            hash.update(block)

    return hash.hexdigest()


def replace_code():
    if constants.paths.CODE_DIR.exists() is True:
        recursive_rmdir(constants.paths.CODE_DIR)
    
    constants.paths.TEMP_DIR.replace(constants.paths.CODE_DIR)
    constants.paths.TEMP_DIR.mkdir()


def read_config():
    exit_code = 0
    exit_msg  = ''

    if constants.paths.CONFIG_FILE.exists() is not True:
        exit_msg = 'Missing config.json file! Exiting...'
        exit = constants.exit_status.MISSING_CONFIG

    # TODO: Use Voluptuous to validate config.json format

    if exit_code != 0:
        print(exit_msg)
        sys.exit(exit_code)
    
    with constants.paths.CONFIG_FILE.open() as config_file:
        configuration = json.load(config_file)

    return configuration
# End of File Handling Section


# Subprocess Management
# ! If not terminated, the child process will still run even if this runner is closed!
def kill_proc_tree(pid, sig=SIGTERM, include_parent=True, timeout=None, on_terminate=None):
    """
    Kill a process tree (including grandchildren) with signal
    "sig" and return a (gone, still_alive) tuple.
    "on_terminate", if specified, is a callback function which is
    called as soon as a child terminates.
    """
    assert pid != psutil.Process().pid, "won't kill myself"
    parent = psutil.Process(pid)
    children = parent.children(recursive=True)
    if include_parent:
        children.append(parent)
    for p in children:
        p.send_signal(sig)
    gone, alive = psutil.wait_procs(children, timeout=timeout,
                                    callback=on_terminate)
    return (gone, alive)


def run_code():
    return psutil.Popen([sys.executable, constants.paths.SCRIPT_FILE])
# End of Subprocess Management


# Multicast Handling Section
def create_multicast_socket(target_address, bind_port):
    try:
        mcast_sock = sock.socket(sock.AF_INET, sock.SOCK_DGRAM)
        mcast_sock.bind(('', bind_port))
    except sock.error:
        print('Failed to create Multicast Socket!')
        sys.exit(constants.exit_status.SOCK_MCAST_CREATE_FAIL)

    try:
        mreq = struct.pack('=4sL', sock.inet_aton(target_address), sock.INADDR_ANY)
        mcast_sock.setsockopt(sock.IPPROTO_IP, sock.IP_ADD_MEMBERSHIP, mreq)
    except sock.error:
        print('Failed to join Multicast Group')
        sys.exit(constants.exit_status.GRP_MCAST_JOIN_FAIL)

    return mcast_sock


def listen_command_messages(mcast_sock, buf_size=1024, separator='|', timeout=None):
    mcast_sock.settimeout(timeout)
    msg, addr = mcast_sock.recvfrom(buf_size)
    return [val.decode() for val in msg.split()], addr


def reply_command_messages(mcast_sock, message, address):
    mcast_sock.sendto(str(message).encode(), address)


def check_free_space(file_size):
    free_space = psutil.disk_usage(str(constants.paths.CURR_DIR)).free
    return float(free_space * 0.95) > float(file_size)


def receive_multicast_data(mcast_socket, file_size ,buf_size=1024):
    with constants.paths.TEMP_DATA_FILE.open(mode='wb') as file:
        total = 0

        while total < file_size:
            file_data, incoming_addr = mcast_socket.recvfrom(buf_size)
            file.write(file_data)
            total += len(file_data)

    return total


def apply_update(target_pid):
        # Empty the TEMP_DIR
    recursive_rmdir(str(constants.paths.TEMP_DIR))

    # Extract files to tempdir
    with zipfile.ZipFile(str(constants.paths.TEMP_DATA_FILE)) as new_zip:
        new_zip.extractall(path=constants.paths.TEMP_DIR)

    kill_proc_tree(target_pid)
    recursive_rmdir(str(constants.paths.CODE_DIR))
    replace_code()
    return run_code()
    

def should_listen(target_id, device_info, is_cluster=False):
    return device_info['id' if is_cluster is False else 'cluster'] == target_id

def handle_ota_update(gateway_params, device_info):
    # Initial Run
    proc = run_code()

    global_multicast_socket = create_multicast_socket(gateway_params['cmd_mcast_addr'], gateway_params['cmd_mcast_port'])
    data_multicast_socket = None

    try:
        while True:
            try:
                #! **STANDBY PHASE**
                #! Standby for gateway instructions 
                cmd_messages, gateway_addr = listen_command_messages(global_multicast_socket,
                                                        buf_size=gateway_params['buffer_size'],
                                                        separator=gateway_params['message_separator'])

                #! Ignore if not session initialization message
                if cmd_messages[0] not in ['c', 'd']:
                    continue


                if should_listen(cmd_messages[1], device_info, cmd_messages[1]=='c') is not True:
                    continue
                
                file_size = int(cmd_messages[2])
                enough_free_space = check_free_space(file_size)
                msg_array = [
                    constants.cmd_code.OK if enough_free_space is True else constants.cmd_code.INSUFFICIENT_DISK, device_info['id']]
                    
                #! Reply about my free size (enough or not enough)
                reply_message = gateway_params['message_separator'].join(msg_array)
                reply_command_messages(global_multicast_socket, reply_message, gateway_addr)

                if enough_free_space is not True:
                    print('File cannot fit into memory!')
                    print('It is advised to leave at least 5% of free disk space')
                    continue

                [data_multicast_addr, data_multicast_port] = cmd_messages[3].split(':')
                data_multicast_socket = create_multicast_socket(data_multicast_addr, data_multicast_port)

                listen_transfer = True

                #! Poll until transfer/abort command
                while True:
                    transfer_messages, gateway_addr = listen_command_messages(global_multicast_socket,
                                                                            buf_size=gateway_params['buffer_size'],
                                                                            separator=gateway_params['message_separator'])

                    if should_listen(transfer_messages[1], device_info, cmd_messages[1] == 'c') is not True:
                        continue

                    listen_transfer = transfer_messages[0] != 'a'
                    
                    if transfer_messages[0] in ['t', 'a']:
                        break

                if listen_transfer is not True:
                    print('Aborting Before Transfer Phase...')
                    continue

                #! **DATA TRANSFER PHASE**
                #! Receive Files (if not abort)
                file_received_len = receive_multicast_data(data_multicast_socket, file_size, gateway_params['buffer_size'])
                do_checksum = True

                #! Poll until checksum/abort command
                while True:
                    checksum_messages, gateway_addr = listen_command_messages(global_multicast_socket,
                                                                            buf_size=gateway_params['buffer_size'],
                                                                            separator=gateway_params['message_separator'], 
                                                                            timeout=3.0)

                    if should_listen(checksum_messages[1], device_info, cmd_messages[1] == 'c') is not True:
                        continue

                    do_checksum = checksum_messages[0] != 'a'                    

                    if checksum_messages[0] in ['h', 'a']:
                        break

                if do_checksum is not True:
                    print('Aborting After Transfer Phase...')

                #! Match Checksum and reply (if not abort)
                server_checksum = checksum_messages[1]
                if server_checksum == md5Checksum(gateway_params['buffer_size']):
                    ack_reply = [constants.cmd_code.ACK, device_info['device_id']]
                else:
                    ack_reply = [constants.cmd_code.HASHSUM_MISMATCH, device_info['device_id']]

                reply_message = gateway_params['message_separator'].join(ack_reply)
                reply_command_messages(global_multicast_socket, reply_message, gateway_addr)

                start_update = True

                #! Poll until startUpdate/abort command
                while True:
                    start_messages, gateway_addr = listen_command_messages(global_multicast_socket,
                                                                            buf_size=gateway_params['buffer_size'],
                                                                            separator=gateway_params['message_separator'],
                                                                            timeout=5.0)

                    if should_listen(start_messages[1], device_info, cmd_messages[1] == 'c') is not True:
                        continue

                    start_update = start_messages[0] == 'a'

                    if start_messages[0] in ['s', 'a']:
                        break

                #! **UPDATE PHASE**
                #! Apply update (if not abort)
                if start_update is True:
                    apply_update(proc.pid)
                else:
                    print('Aborting Update Phase...')
            except sock.timeout:
                print('Socket timed out!')
            finally:
                if type(data_multicast_socket) is sock.socket:
                    data_multicast_socket.close()

                data_multicast_socket = None

                if constants.paths.TEMP_DATA_FILE.exists() is True:
                    constants.paths.TEMP_DATA_FILE.unlink()
    finally:
        if type(global_multicast_socket) is sock.socket:
            global_multicast_socket.close()
    
    
# End of Multicast Handling Section


def main():
    configuration = read_config()

    # Check existence appropriate script file
    if constants.paths.SCRIPT_FILE.exists() is not True:
        print('Missing Initialization Script File!')
        sys.exit(constants.exit_status.MISSING_SCRIPT)

    # Check Dirs and create if missing
    dirs = [
        constants.paths.CODE_DIR,
        constants.paths.TEMP_DIR,
    ]

    for dir in dirs:
        if dir.exists() is not True:
            dir.mkdir()

    # Send Initialization request to gateway address
    try:
        response = requests.post(configuration['gateway_url'] + configuration['init_api_path'], json=configuration['device_info'])

        if response.raise_for_status() is None:
            json_data = response.json()
            # TODO: Validate JSON Response with Voluptuous

            if json_data['status'] == 'success':
                handle_ota_update(response.json(), configuration['device_info'])
            else:
                print(json_data)
                sys.exit(constants.exit_status.GATEWAY_FAILURE)
        else:
            raise requests.HTTPError
    except requests.HTTPError as err:
        print(err)
        sys.exit(constants.exit_status.HTTP_ERROR)


if __name__ == '__main__':
    main()
    sys.exit(constants.exit_status.SUCCESS)

# Test This
