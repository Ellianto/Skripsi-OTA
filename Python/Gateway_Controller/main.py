import hashlib
import json
import socket as sock
import socketserver
import struct
import sys
import time
from pathlib import Path
from subprocess import PIPE

import psutil

import constants
import paho.mqtt.client as mqtt
import requests
from voluptuous import MultipleInvalid

# Globals
mqtt_client = None
cmd_mcast_socket = None
data_mcast_socket = None

def init_device_to_server(json_data):
    status = False

    try:
        response = requests.put(constants.network.INIT_DEVICE_ENDPOINT, json=json_data)

        if response.raise_for_status() is None:
            json_response = constants.json_schema.SERVER_RESPONSE_VALIDATOR(response.json())
            status = json_response['status'] == 'success'
        else:
            raise requests.HTTPError
    except requests.HTTPError:
        print(constants.messages.HTTP_ERROR_MESSAGE)
        print('HTTP Code : ' + str(response.status_code) + ' ' + response.reason)
    except ConnectionError:
        print(constants.messages.CONNECTION_ERROR_MESSAGE)
    except TimeoutError:
        print(constants.messages.TIMEOUT_ERROR_MESSAGE)
    except (ValueError, MultipleInvalid):
        print(constants.messages.INVALID_JSON_MESSAGE)

    return status


def init_device_to_file(json_data):
    # Add to devices.json
    devices_list = get_devices()
    device_exists = next((device for device in devices_list['data'] if device['id'] == json_data['id']), None) is not None

    if device_exists is not True:
        devices_list['data'].append(json_data)

        # Write to devices.json
        with constants.paths.DEVICES_FILE_PATH.open(mode='w') as devices_file:
            json.dump(devices_list, devices_file, skipkeys=True,
                        ensure_ascii=True, indent=4)

        # Add to clusters.json if cluster member
        if json_data['cluster'] is not None:
            clusters_list = get_clusters()
            cluster_idx = next((idx for idx, cluster in enumerate(clusters_list['data']) if cluster['id'] == json_data['cluster']), None)
            
            if cluster_idx is None:
                # Cluster not in list, append
                clusters_list['data'].append({
                    'id' : json_data['cluster'],
                    'type' : json_data['type'],
                    'devices' : [json_data['id']]
                })

            else:
                device_in_cluster = json_data['id'] in clusters_list['data'][cluster_idx]['devices']

                if device_in_cluster is not True:
                    clusters_list['data'][cluster_idx]['devices'].append(json_data['id'])

            # Write to clusters.json
            with constants.paths.CLUSTERS_FILE_PATH.open(mode='w') as clusters_file:
                json.dump(clusters_list, clusters_file, skipkeys=True,
                        ensure_ascii=True, indent=4)


class MyTCPHandler(socketserver.StreamRequestHandler):
    """
    The request handler class for our server.

    It is instantiated once per connection to the server, and must
    override the handle() method to implement communication to the
    client.
    """

    def handle(self):
        configuration = get_config()
        # Note that the serialized JSON needs to be newline terminated
        client_response = self.rfile.readline().decode().strip()
        received_json = json.loads(client_response)
        self.data = constants.json_schema.END_DEVICE_CONF_VALIDATOR(
            received_json)

        # Defaults to rejected
        self.reply_json = {'status': 'rejected'}

        if self.data['code'] in ['INIT']:
            device_data = {
                'id' : str(self.data['id']),
                'cluster' : None if str(self.data['cluster']) == '' else str(self.data['cluster']),
                'type' : str(self.data['type']) 
            }

            # Forward to Server
            init_success = init_device_to_server({
                'gateway': str(configuration['gateway_uid']),
                **device_data
            })

            if init_success is True:
                init_device_to_file(device_data)
                
                # Reply Back to client
                [cmd_mcast_addr, cmd_mcast_port] = str(
                    configuration['end_device_multicast_addr']).split(':')

                self.reply_json = {
                    'status': 'success',
                    'msg_separator': constants.network.CMD_MSG_SEPARATOR,
                    'cmd_mcast_addr': cmd_mcast_addr,
                    'cmd_mcast_port': cmd_mcast_port
                }

            else:
                self.reply_json = {'status' : 'failed'}

        encoded_json = (json.dumps(self.reply_json)).encode()
        self.wfile.write(encoded_json)


# Initializer Functions

def init_conf(retries=0):
    print('Initializing Configuration...')
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
                            'end_device_multicast_addr' : conf_data['end_device_multicast_addr'],
                        }

                        json.dump(config, conf_file, indent=4,
                                skipkeys=True, sort_keys=True, ensure_ascii=True)

                else:
                    raise requests.HTTPError

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


def init_dirs_and_json_files():
    print('Initializing Directories and JSON Files...')

    dirs = constants.paths.DIR_LIST
    json_files = constants.paths.JSON_FILE_LIST

    init_json = {'data' : []}

    for dir in dirs:
        if dir.exists() is not True:
            print('Directory {} not detected! Creating...'.format(str(dir)))
            dir.mkdir(parents=True)
        else:
            print('Directory {} checked, exists'.format(str(dir)))

    for json_file in json_files:
        if json_file.exists() is not True:
            print('JSON file {} missing! Creating...'.format(str(json_file)))

            with json_file.open(mode='w') as file:
                json.dump(init_json, file, indent=4, ensure_ascii=True)
        else:
            print('JSON File {} checked, exists!'.format(str(json_file)))


def init_uftp():
    print('Initializing UFTP Client daemon...')

    init_dirs_and_json_files()
    return_code = None

    uftp_dir_exists = constants.paths.UFTP_DIR.exists()
    uftp_client_exe_exists = constants.paths.UFTP_CLIENT_EXE_PATH.exists()

    try:
        if uftp_client_exe_exists is not True or uftp_dir_exists is not True:
            return_code = 3
        else:
            proc_name = 'uftpd'
            uftpd_instance = next(proc for proc in psutil.process_iter() if proc.name() == proc_name)
            print('UFTP Client Daemon already running!')
            return_code = 1
    except StopIteration:
        configuration = get_config()

        uftp_client_cmd = [str(constants.paths.UFTP_CLIENT_EXE_PATH), '-t',
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
    print('Initializing Multicast Socket...')


    rc = 0
    with constants.paths.CONF_FILE_PATH.open() as conf_file:
        configuration = json.load(conf_file)

    [cmd_mcast_addr, cmd_mcast_port] = str(configuration['end_device_multicast_addr']).split(':')

    try:
        cmd_mcast_socket = sock.socket(sock.AF_INET, sock.SOCK_DGRAM)
        ip_addr = constants.network.AP_ADDRESS
        cmd_mcast_socket.bind((ip_addr, int(cmd_mcast_port)))
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
    print('Initializing MQTT Client...')
    rc = False
    try:
        configuration = get_config()
        mqtt_client = mqtt.Client(configuration['gateway_uid'])
        mqtt_client.on_connect = on_mqtt_connect
        mqtt_client.on_message = on_mqtt_message

        mqtt_client.connect(configuration['mqtt_broker'], bind_address=constants.network.WLAN_ADDRESS)
        mqtt_client.loop_start()
        rc = True
    except Exception as err:
        print(err)
        # raise

    return rc

# End of initializers

# File Functions

def get_config():
    with constants.paths.CONF_FILE_PATH.open() as config_file:
        configuration = json.load(config_file)
    return configuration


def get_devices():
    with constants.paths.DEVICES_FILE_PATH.open() as devices_file:
        devices = json.load(devices_file)

    return devices


def get_clusters():
    with constants.paths.CLUSTERS_FILE_PATH.open() as clusters_file:
        clusters = json.load(clusters_file)

    return clusters


def read_in_chunks(file_obj, chunk_size=1024):
    while True:
        chunk_data = file_obj.read(chunk_size)
        if not chunk_data:
            break

        yield chunk_data


def get_file_size(file_obj):
    file_obj.seek(0, 2)
    size = file_obj.tell()
    file_obj.seek(0)
    return str(size)


def md5_checksum(file_path, block_size=1024):
    hash = hashlib.md5()
    with file_path.open(mode='rb') as f:
        for block in iter(lambda: f.read(block_size), b''):
            hash.update(block)

    return hash.hexdigest()


# End of File Functions

# Multicast Functions
# TODO: Randomize this later
def generate_data_mcast_addr():
    return ('225.2.2.5', 5222)


def send_mcast_cmd(cmd_arr, dest_addr):
    cmd_mcast_socket.sendto(
        (constants.network.CMD_MSG_SEPARATOR.join(cmd_arr) + '\n').encode(),
        dest_addr
    )


def listen_for_reply(mcast_sock, buf_size=1024):
    reply, addr = mcast_sock.recvfrom(buf_size)
    print('Reply from ' + addr)
    return [val.decode() for val in reply.split(constants.network.CMD_MSG_SEPARATOR)]


def multicast_update(target_id, is_cluster=False):
    #! **START PHASE**
    #! Get required params and infos
    configuration = get_config()

    devices = get_devices()
    target_clients = [device['id'] for device in devices['data'] if device['id' if is_cluster is False else 'cluster'] == target_id]
    abort_msg = [
        'a',
        str(target_id),
        configuration['gateway_uid']
    ]

    # So that the usage of this variable in the function
    # refers to the global variable that has been initialized
    global cmd_mcast_socket

    cmd_mcast_addr = str(configuration['end_device_multicast_addr']).split(':')
    cmd_mcast_group = (cmd_mcast_addr[0], int(cmd_mcast_addr[1]))
    data_mcast_group = generate_data_mcast_addr()

    # TODO: Check if the path is correct when testing
    target_file_path = constants.paths.DEST_DIR / ('clusters' if is_cluster is True else 'devices') / target_id /  (target_id + '.zip')
    target_file = target_file_path.open(mode='rb')
    checksum = md5_checksum(target_file_path)

    #! **STANDBY PHASE**
    #! Send target cluster/device ID and additional info
    channel_setup_msg = [
        'c' if is_cluster is True else 'd',
        str(target_id), 
        get_file_size(target_file), 
        data_mcast_group[0],
        data_mcast_group[1]
    ]

    send_mcast_cmd(channel_setup_msg, cmd_mcast_addr)

    #! Poll for client response
    # Expected message format : [OK or NO or FA]|[device_id]|[possible_buffer_size]\n
    clients_ok = False
    clients_replied = []
    buffer_limit = 1460

    while True:
        try:
            reply_messages = listen_for_reply(cmd_mcast_socket, buf_size=configuration['buffer_size'])

            print('Received ' + reply_messages[0] + ' from ' + reply_messages[1])

            if reply_messages[0] == 'OK' and reply_messages[1] in target_clients:
                clients_replied.append(reply_messages[1])

                client_buffer_size = reply_messages[2]

                over_limit = buffer_limit > client_buffer_size

                if over_limit is True:
                    buffer_limit = client_buffer_size
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
            
    #! If not all clients are OK, send abort
    if clients_ok is not True:
        # Exit early
        cmd_mcast_socket.sendto((constants.network.CMD_MSG_SEPARATOR.join(abort_msg)).encode(),
                                cmd_mcast_group)
        return 1

    #! Create Data Mcast Socket
    try:
        data_mcast_socket = sock.socket(sock.AF_INET, sock.SOCK_DGRAM)
    except sock.error:
        print('Failed to create Data Multicast Socket!')
        send_mcast_cmd(abort_msg, cmd_mcast_addr)
        return 2

    #! **TRANSFER PHASE**
    #! Tell clients to start listening
    begin_transfer_msg = [
        't',
        str(target_id),
        str(checksum),
        buffer_limit,
    ]

    time.sleep(0.3)
    send_mcast_cmd(begin_transfer_msg, cmd_mcast_addr)
    time.sleep(0.7)

    #! Send chunks of file to client
    for piece in read_in_chunks(target_file):
        data_mcast_socket.sendto(piece, data_mcast_group)
        time.sleep(0.03)

    #! Close Data Socket
    data_mcast_socket.close()

    #! **VERIFICATION PHASE**
    #! Poll for client response
    # Expected message format : [ACK or NEQ or DTO]|[device_id]\n
    clients_acked = []
    transfer_ok = False

    while True:
        try:
            reply_messages = listen_for_reply(
                cmd_mcast_socket, buf_size=configuration['buffer_size'])

            print('Received ' + reply_messages[0] + ' from ' + reply_messages[1])

            if reply_messages[0] == 'ACK' and reply_messages[1] in clients_replied:
                clients_acked.append(reply_messages[1])
            elif clients_acked[0] in ['NEQ', 'DTO']:
                break
        except sock.timeout:
            print('Some clients failed to reply!')
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

    #! **END PHASE**
    #! Tell them to replace the old code or to actually do the update
    apply_update_msg = [
        's',
        str(target_id),
        configuration['gateway_uid']
    ]

    send_mcast_cmd(apply_update_msg, cmd_mcast_addr)
    time.sleep(3)
    #! To force stop any "hanging clients"
    send_mcast_cmd(abort_msg, cmd_mcast_addr)
    return 0


# End of Multicast Functions

# MQTT Functions
def on_mqtt_connect(client, userdata, flags, rc):
    if rc == 0:
        configuration = get_config()
        (result, mid) = client.subscribe(
                configuration['mqtt_topic'], qos=2)

        if result == mqtt.MQTT_ERR_SUCCESS:
            active_msg = [
                'init',
                configuration['gateway_uid']
            ]

            client.publish(configuration['mqtt_topic'], constants.network.CMD_MSG_SEPARATOR.join(active_msg).encode(), qos=2)
    
    if rc in range(len(constants.mqtt.RETURN_CODE_MESSAGES)):
        print(constants.mqtt.RETURN_CODE_MESSAGES[rc])
    else:
        print(constants.mqtt.INVALID_RETURN_CODE)


def on_mqtt_message(client, userdata, msg):
    print("Message Received from topic " + str(
        msg.topic) + ' : ' + str(msg.payload.decode()))

    mqtt_message = msg.payload.decode().split(constants.network.CMD_MSG_SEPARATOR)

    if mqtt_message[0] == constants.mqtt.UPDATE_CODE:
        target_id = str(mqtt_message[2])

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
            print('Starting TCP Socket Server...')
            with socketserver.TCPServer((constants.network.AP_ADDRESS, 6666), MyTCPHandler) as server:
                # Activate the server; this will keep running until you
                # interrupt the program with Ctrl-C
                server.serve_forever()

    finally:
        if cmd_mcast_socket is not None:
            configuration = get_config()
            [cmd_mcast_addr, cmd_mcast_port] = str(configuration['end_device_multicast_addr']).split(':')

            mreq = struct.pack('=4sL', sock.inet_aton(cmd_mcast_addr), sock.INADDR_ANY)
            cmd_mcast_socket.setsockopt(sock.IPPROTO_IP, sock.IP_DROP_MEMBERSHIP, mreq)

            cmd_mcast_socket.close()

        if mqtt_client is not None:
            mqtt_client.loop_stop()
            mqtt_client.disconnect()

    sys.exit(rc)
