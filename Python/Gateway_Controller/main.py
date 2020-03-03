import json
from pathlib import Path
from subprocess import PIPE
import socket as sock
import struct
import hashlib
import sys
import time

import psutil

import paho.mqtt.client as mqtt
import requests
from voluptuous import MultipleInvalid
import constants

# TODO: Create a simple server

# Globals
mqtt_client = None
cmd_mcast_socket = None
data_mcast_socket = None

# Initializer Functions

def init_conf(retries=2):
    conf_ready = False
    attempts = 0

    while attempts <= retries and conf_ready is False:
        attempts += 1

        try:
            if constants.paths.CONF_FILE_PATH.exists() is not True:
                response = requests.get(constants.network.INIT_GATEWAY_ENDPOINT)

                if response.raise_for_status() is None:
                    if response.json()['status'] == 'error':
                        continue

                    conf_data = constants.json_schema.SERVER_CONF_VALIDATOR(response.json())

                    with constants.paths.CONF_FILE_PATH.open(mode='w') as conf_file:
                        config = {
                            'mqtt_topic' : conf_data['mqtt_topic'],
                            'mqtt_broker' : conf_data['mqtt_broker'],
                            'gateway_uid' : conf_data['gateway_uid'],
                            'max_log_size' : conf_data['max_log_size'],
                            'max_log_count' : conf_data['max_log_count'],
                            'buffer_size' : conf_data['buffer_size'],
                            'end_device_multicast_addr' : conf_data['end_device_multicast_addr'],
                        }

                        json.dump(config, conf_file, indent=4,
                                skipkeys=True, sort_keys=True, ensure_ascii=True)

                else:
                    raise requests.HTTPError

            conf_data = constants.json_schema.SERVER_CONF_VALIDATOR(get_config())
            conf_ready = True

        except requests.HTTPError:
            print(constants.messages.HTTP_ERROR_MESSAGE)
            print('HTTP Code : ' + str(response.status_code) + ' ' + response.reason)
        except ConnectionError:
            print(constants.messages.CONNECTION_ERROR_MESSAGE)
        except TimeoutError:
            print(constants.messages.TIMEOUT_ERROR_MESSAGE)
        except (ValueError, MultipleInvalid):
            print(constants.messages.INVALID_JSON_MESSAGE)

    return conf_ready


def init_dirs():
    dirs = [constants.paths.DEST_DIR, constants.paths.BACKUP_DIR]

    for dir in dirs:
        if dir.exists() is not True:
            print('Directory {} not detected, creating directory...'.format(str(dir)))
            dir.mkdir(parents=True)
        else:
            print('Directory {} checked, exists'.format(str(dir)))


def init_uftp():
    init_dirs()
    return_code = None

    uftp_dir_exists = constants.paths.UFTP_DIR.exists()
    uftp_client_exe_exists = constants.paths.UFTP_CLIENT_EXE_PATH.exists()

    try:
        if uftp_client_exe_exists is not True or uftp_dir_exists is not True:
            return_code = 3
        else:
            proc_name = 'uftpd.exe'
            uftpd_instance = next(proc for proc in psutil.process_iter() if proc.name() == proc_name)
            print('UFTP Client Daemon already running!')
            return_code = 1
    except StopIteration:
        configuration = get_config()

        uftp_client_cmd = [str(constants.paths.UFTP_CLIENT_EXE_PATH), '-d', '-t',
                            '-A', str(constants.paths.BACKUP_DIR),
                            '-D', str(constants.paths.DEST_DIR),
                            '-L', str(constants.paths.LOG_FILE_PATH),
                            '-F', str(constants.paths.STATUS_FILE_PATH),
                            '-U', str(configuration['gateway_uid']),
                            '-g', str(configuration['max_log_size']),
                            '-n', str(configuration['max_log_count'])]

        with psutil.Popen(uftp_client_cmd) as uftp_client_daemon:
            if uftp_client_daemon.is_running() is True:
                print('Started UFTP Client Daemon with PID : {}'.format(
                    uftp_client_daemon.pid))
                return_code = 0
            else:
                print('Something wrong happened while starting UFTP Client Daemon!')
                print('Status : {}'.format(uftp_client_daemon.status()))
                return_code = 2
    except:
        print('Something Happened!')
        raise

    return return_code


def init_multicast():
    rc = 0
    with constants.paths.CONF_FILE_PATH.open() as conf_file:
        configuration = json.load(conf_file)

    [cmd_mcast_addr, cmd_mcast_port] = str(configuration['end_device_multicast_addr']).split(':')

    try:
        cmd_mcast_socket = sock.socket(sock.AF_INET. sock.SOCK_DGRAM)
        ip_addr = constants.paths.AP_ADDRESS
        cmd_mcast_socket.bind((ip_addr, cmd_mcast_port))
    except sock.error:
        print('Failed to create Multicast Socket!')
        rc = 1


    try:
        mreq = struct.pack('=4sL', sock.inet_aton(cmd_mcast_addr), sock.INADDR_ANY)
        cmd_mcast_socket.setsockopt(sock.IPPROTO_IP, sock.IP_ADD_MEMBERSHIP, mreq)
    except sock.error:
        print('Failed to join Multicast Group!')
        rc = 2

    cmd_mcast_socket.settimeout(10)
    return rc


def init_mqtt():
    try:
        configuration = get_config()
        mqtt_client = mqtt.Client(client_id=configuration['gateway_uid'])
        mqtt_client.on_connect = on_mqtt_connect
        mqtt_client.on_message = on_mqtt_message

        mqtt_client.will_set(configuration['mqtt_topic'], payload='will|{}'.format(configuration['gateway_uid']))

        userdata = {'gateway_id' : configuration['gateway_id']}

        mqtt_client.user_data_set(userdata)
        mqtt_client.connect(configuration['mqtt_broker'])
        return True
    except Exception as err:
        print(err)
        return False

# End of initializers

# File Functions

def get_config():
    with constants.paths.CONFIG_FILE_PATH.open() as config_file:
        configuration = json.load(config_file)
    return configuration


def get_devices():
    with constants.paths.DEVICES_FILE_PATH.open() as device_file:
        devices = json.load(device_file)

    return devices


def read_in_chunks(file_obj, chunk_size=buffer_size):
    while True:
        chunk_data = file_obj.read(chunk_size)
        if not chunk_data:
            break

        yield chunk_data


def getFileSize(file_obj):
    file_obj.seek(0, 2)
    size = file_obj.tell()
    file_obj.seek(0)
    return str(size)


def md5Checksum(file_path, block_size=1024):
    hash = hashlib.md5()
    with file_path.open(mode='rb') as f:
        for block in iter(lambda: f.read(block_size), b''):
            hash.update(block)

    return hash.hexdigest()


# End of File Functions

# Multicast Functions
# Might want to randomize this
def generate_data_mcast_addr():
    return ('225.2.2.5', 5222)


def send_mcast_cmd(cmd_arr, dest_addr):
    cmd_mcast_socket.sendto(
        (constants.network.CMD_MSG_SEPARATOR.join(cmd_arr)).encode(),
        dest_addr
    )


def listen_for_reply(mcast_sock, buf_size=1024):
    reply, addr = mcast_sock.recvfrom(buf_size)
    print('Reply from ' + addr)
    return [val.decode() for val in reply.split(constants.network.CMD_MSG_SEPARATOR)]


def multicast_update(target_id, is_cluster=False):
    #! Get requred params and infos
    devices = get_devices()
    target_clients = [device['id'] for device in devices['list'] if device['id' if is_cluster is False else 'cluster'] == target_id]
    abort_msg = [
        'a',
        str(target_id)
    ]

    # So that the usage of this variable in the function
    # refers to the global variable that has been initialized
    global cmd_mcast_socket

    configuration = get_config()

    cmd_mcast_addr = str(configuration['end_device_multicast_addr']).split(':')
    cmd_mcast_group = (cmd_mcast_addr[0], int(cmd_mcast_addr[1]))
    data_mcast_group = generate_data_mcast_addr()

    # TODO: Check if the path is correct when testing
    target_file_path = constants.paths.DEST_DIR / ('clusters' if is_cluster is True else 'devices') / target_id /  (target_id + '.zip')
    target_file = target_file_path.open(mode='rb')
    hashsum = md5Checksum(target_file_path)

    #! **MAIN PHASE**
    #! Send target cluster/device ID and additional info
    channel_setup_msg = [
        'c' if is_cluster is True else 'd',
        str(target_id), 
        getFileSize(target_file), 
        ':'.join(map(str, data_mcast_group))
    ]

    send_mcast_cmd(channel_setup_msg, cmd_mcast_addr)

    clients_ok = False
    clients_replied = []

    #! Poll for client response
    while True:
        try:
            reply_messages = listen_for_reply(cmd_mcast_socket, buf_size=configuration['buffer_size'])

            if reply_messages[0] == 'OK' and reply_messages[1] in target_clients:
                clients_replied.append(reply_messages[1])
            elif clients_replied[0] in ['NO', 'FA']:
                break
        except sock.timeout:
            print('Some clients did not respond!')
            break
        except OSError:
            print('Specified Buffer Size is not enough!')
            send_mcast_cmd(abort_msg, cmd_mcast_addr)
            break
        else:
            if set(target_clients) == set(clients_replied):
                clients_ok = True
                break
            

    if clients_ok is not True:
        # Exit early
        cmd_mcast_socket.sendto((constants.network.CMD_MSG_SEPARATOR.join(abort_msg)).encode(),
                                cmd_mcast_group)
        return 1

    #! **DATA TRANSFER PHASE**
    #! Create Data Mcast Socket
    try:
        data_mcast_socket = sock.socket(sock.AF_INET, sock.SOCK_DGRAM)
    except sock.error:
        print('Failed to create Data Multicast Socket!')
        send_mcast_cmd(abort_msg, cmd_mcast_addr)
        return 2

    #! Tell clients to start listening
    begin_transfer_msg = [
        't',
        str(target_id)
    ]
    time.sleep(0.5)
    send_mcast_cmd(begin_transfer_msg, cmd_mcast_addr)
    time.sleep(0.5)

    #! Send chunks of file to client
    for piece in read_in_chunks(target_file):
        data_mcast_socket.sendto(piece, data_mcast_group)
        time.sleep(0.03)

    #! Close Data Socket
    data_mcast_socket.close()

    #! **END PHASE**
    #! Send File Hashsum for integrity check
    hashsum_msg = [
        'h',
        str(hashsum)
    ]
    time.sleep(1)
    send_mcast_cmd(hashsum_msg, cmd_mcast_addr)

    clients_acked = []
    transfer_ok = False

    #! Poll for client response
    while True:
        try:
            reply_messages = listen_for_reply(
                cmd_mcast_socket, buf_size=configuration['buffer_size'])

            if reply_messages[0] == 'ACK' and reply_messages[1] in target_clients:
                clients_replied.append(reply_messages[1])
            elif clients_replied[0] in ['NEQ']:
                break
        except sock.timeout:
            print('Some clients failed to ACK')
            break
        except OSError:
            print('Specified Buffer size is not enough!')
            send_mcast_cmd(abort_msg, cmd_mcast_addr)
            break
        else:
            if set(clients_acked) == set(clients_replied):
                transfer_ok = True
                break

    if transfer_ok is not True:
        send_mcast_cmd(abort_msg, cmd_mcast_addr)
        return 2

    #! Tell them to replace the old code or to actually do the update
    apply_update_msg = [
        's',
        str(target_id)
    ]

    send_mcast_cmd(apply_update_msg, cmd_mcast_addr)
    time.sleep(3)
    #! To force stop any "hanging clients"
    send_mcast_cmd(abort_msg, cmd_mcast_addr)
    return 0

# Fires when a device "registers/initializes"
# Reply with addresses and other infos
# And send init data to server telling this device is initializing
# Also, save the client data into local
# TODO: run in background as a separate process
def end_device_connect_callback():
    # Fetch JSON data from end device request
    # TODO: Validate using voluptuous?
    json_data = {}
    configuration = get_config()

    # Send Request to server first
    try:
        response = requests.post(constants.network.INIT_DEVICE_ENDPOINT, json={
            'gateway' : str(configuration['gateway_uid']),
            **json_data
        })

        if response.raise_for_status() is None:
            pass
        else:
            raise requests.HTTPError
    except requests.HTTPError:
        print(constants.messages.HTTP_ERROR_MESSAGE)
        print('HTTP Code : ' + str(response.status_code) +
                ' ' + response.reason)
    except ConnectionError:
        print(constants.messages.CONNECTION_ERROR_MESSAGE)
    except TimeoutError:
        print(constants.messages.TIMEOUT_ERROR_MESSAGE)
    except (ValueError, MultipleInvalid):
        print(constants.messages.INVALID_JSON_MESSAGE)
    
    
    # If Response is okay, then continue

    devices_file_exists = constants.paths.DEVICES_FILE_PATH.exists()

    if devices_file_exists is True:
        json_list = get_devices()
        json_list['list'].append(json_data)
    else:
        json_list = {'list' : [json_data]}

    # Write to devices.json
    with constants.paths.DEVICES_FILE_PATH.open(mode='w') as devices_file:
        json.dump(json_list, devices_file, skipkeys=True,
                  ensure_ascii=True, indent=4)

    # Reply to end-device regardless of successfully connected to server or not
    [cmd_mcast_addr, cmd_mcast_port] = str(
        configuration['end_device_multicast_addr']).split(':')

    json_reply = {
        'buffer_size' : configuration['buffer_size'],
        'message_separator' : constants.network.CMD_MSG_SEPARATOR,
        'cmd_mcast_addr' : cmd_mcast_addr,
        'cmd_mcast_port' : cmd_mcast_port
    }


# End of Multicast Functions

# MQTT Functions
def on_mqtt_connect(client, userdata, flags, rc):
    if rc == 0:
        configuration = get_config()
        (result, mid) = mqtt_client.subscribe(
                configuration['mqtt_topic'], qos=2)
    
    if rc in range(len(constants.mqtt.RETURN_CODE_MESSAGES)):
        print(constants.mqtt.RETURN_CODE_MESSAGES[rc])
    else:
        print(constants.mqtt.INVALID_RETURN_CODE)


def on_mqtt_message(client, userdata, msg):
    print("Message Received from topic " + str(
        msg.topic) + ' : ' + str(msg.payload.decode()))

    mqtt_message = msg.payload.decode().split('|')

    if mqtt_message[0] == constants.mqtt.UPDATE_CODE:
        target_id = str(mqtt_message[2])
        # TODO: Inspect Return code (if fail, probably report to an endpoint)
        attempts = 0
        messages = ['Success!', 'Some target clients failed to connect!', 'Data Transfer not successful!']

        for attempts in range(3):
            return_code = multicast_update(target_id, is_cluster=(str(mqtt_message[1]) == 'cluster'))
            print('Multicast Firmware Update returns ' + str(return_code))
            print(messages[return_code])
            if return_code in [0]:
                break

    elif mqtt_message[0] == constants.mqtt.DEVICE_CODE:
        pass

# End of MQTT Functions


# CLI Entry point
if __name__ == '__main__':
    rc = 0
    try:
        if init_conf() is not True:
            print('Error while getting configuration from Server!')
            rc = 1
        elif init_uftp() not in [0, 1]:
            print('Error while starting UFTP Client Daemon!')
            rc = 2
        elif init_multicast() not in [0]:
            print('Error while initializing Multicast Socket!')
            rc = 3
        elif init_mqtt() is not True:
            print('Error while initializing MQTT Client!')
            rc = 4
        else:
            mqtt_client.loop_forever()
    finally:
        if type(cmd_mcast_socket) is sock.socket:
            cmd_mcast_socket.close()

    sys.exit(rc)
