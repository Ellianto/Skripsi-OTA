import json
import random
from pathlib import Path
from subprocess import PIPE

import psutil

from flask import Flask, abort, jsonify, request
from flask_mqtt import Mqtt
from voluptuous import (All, Any, Coerce, Length, Match, Maybe,
                        MultipleInvalid, Required, Schema)

# TODO: Handle delete event for gateway/controller side
# TODO: Handle disconnect event, if possible
# TODO: Refactor

app = Flask(__name__)

global_topic = 'ota/control'
cluster_topic = 'ota/cluster'

curr_dir = Path(__file__).parent.absolute()

base_dir = curr_dir / 'data'

path_to_devices_file =  base_dir / 'devices.json'
path_to_clusters_file = base_dir / 'clusters.json'
path_to_gateways_file = base_dir / 'gateways.json'

uftp_dir = curr_dir / 'uftp' 

status_file = uftp_dir / 'status.txt'
log_file = uftp_dir / 'uftp_server_logfile.txt'
path_to_uftp_server_exe = uftp_dir / 'uftp.exe'

# TODO: Might have to add randomizer to this (with a certain range) later
port_number = '1044'  # Default from the UFTP manual
pub_multicast_addr = '230.4.4.1'  # Default from the UFTP manual
# Default from the UFTP manual, the 'x' will be randomized
prv_multicast_addr = '230.5.5.x'
end_device_multicast_addr = '230.6.6.1'

process_timeout = 30  # How long to wait (seconds) before declaring the UFTP Process to be timed out

# UFTP Manual defaults to IPv4 address (converted to Hex) or last 4 bytes of IPv6 address
server_uid = '0xABCDABCD'
transfer_rate = '1024'

robustness = '20' 
max_log_size = '2'  
max_log_count = '5'  

# Still need to append client list and file list/target direactory
uftp_server_cmd = [str(path_to_uftp_server_exe),
                '-l',  # Unravel Symbolic Links
                '-z',  # Run the Server in Sync Mode, so clients will only receive new/updated files
                '-t', '3',  # TTL value for Multicast Packets, by default is 1 so we turn it up a little
                '-U', server_uid,  # Server UID for identification purposes. 
                '-R', transfer_rate, # Transfer rate (Kbps), defaults to 1000 Kbps. 1024 Kbps = 128KB/s
                '-E', str(base_dir), # Base directory for the files, for client-side directory management
                '-S', str(status_file), # Output for status file, to confirm the file transfer result. 
                '-L', str(log_file), # The log file output. If undefined, defaults to printing logs to stderr
                '-g', max_log_size,  # in MB, specifies limit size before a log file is backed up
                '-n', max_log_count, # Default UFTP Value, keeps max 5 iterations of log backups
                '-p', port_number,  # The port number the server will be listening from
                '-M', pub_multicast_addr,  # The Initial Public Multicast Address for the ANNOUNCE phase
                '-P', prv_multicast_addr,  # The Private Multicast Address for FILE TRANSFER phase
                '-s', robustness, # The number of times a message will be repeated (10-50). defaults to 20
                '-H']  # List of comma separated target client IDs, enclosed in "" if more than one


# use the free broker from HIVEMQ
mqtt_broker = 'broker.hivemq.com'

app.config['MQTT_CLIENT_ID'] = 'main_server'
app.config['MQTT_BROKER_URL'] = mqtt_broker
app.config['MQTT_BROKER_PORT'] = 1883
app.config['MQTT_KEEPALIVE'] = 5
app.config['MQTT_TLS_ENABLED'] = False

mqtt = Mqtt(app)

# JSON Validation Schemas
id_validator = All(Coerce(str, msg='Invalid variable type, expected str'), Length(
    min=8, max=30, msg='Invalid Length, expected 8-30 char'), Match(r'^[A-Za-z_][A-Za-z0-9_]{7,29}$'))

device_schema = Schema({
    Required('id'): id_validator,
    Required('type', default=None): Maybe(str, msg='Invalid "type" variable, expected str or None'),
    Required('cluster', default=None): Any(Maybe(str, msg='Invalid "cluster" variable, expected str or None'), id_validator)
})

cluster_schema = Schema({
    Required('id'): id_validator,
    Required('type', default=None): Maybe(str, msg='Invalid "type" variable, expected str or None'),
    Required('devices', default=list): list,
    Required('gateways', default=list): list,
})

# Internal Functions

def generate_gateway_uid():
    with path_to_gateways_file.open() as gateways_file:
        gateways = json.load(gateways_file)

    while True:
        random_hexa_uid = '0x%08X' % random.randrange(16**8)
        gateway_exists = random_hexa_uid in (
            gateway['id'] for gateway in gateways['data'])

        if gateway_exists is False:
            break

    new_gateway = {
        "id": random_hexa_uid,
        "list": {
            "cluster": [],
            "device": [],
        }
    }

    gateways['data'].append(new_gateway)

    with path_to_gateways_file.open(mode='w') as gateways_file:
        json.dump(gateways, gateways_file, indent=4, ensure_ascii=True)

    return random_hexa_uid


def check_item_exists(item_id, item_type='device'):
    target_file = path_to_devices_file

    if item_type == 'cluster':
        target_file = path_to_clusters_file
    elif item_type == 'gateway':
        target_file = path_to_gateways_file

    with target_file.open() as json_file:
        items = json.load(json_file)['data']
        item_exists = [item for item in items if item['id'] == item_id]

    return len(item_exists) > 0


def check_device_membership(device_id):
    with path_to_devices_file.open() as devices_file:
        devices = json.load(devices_file)['data']
        device_membership = next((device for device in devices if device['id'] == device_id), {'cluster':None})
    
    return device_membership['cluster']


def init_files():
    init_data = {"data": []}
    files = [path_to_devices_file,
             path_to_clusters_file, path_to_gateways_file]

    for file in files:
        if not file.exists():
            with file.open(mode='w') as json_file:
                json.dump(init_data, json_file, indent=4, ensure_ascii=True)


def init_dirs():
    dirs = [base_dir / 'clusters', base_dir / 'devices']

    for dir in dirs:
        if dir.exists() is not True:
            dir.mkdir(parents=True)


def register_to_gateway(device_data):
    try:
        # Modify the Device Data
        with path_to_devices_file.open() as device_input:
            devices = json.load(device_input)
            device_index = next(idx for idx, device in enumerate(
                devices['data']) if device['id'] == device_data['id'])
            devices['data'][device_index] = device_data

        with path_to_devices_file.open(mode='w') as device_output:
            json.dump(devices, device_output, indent=4,
                      skipkeys=True, sort_keys=True, ensure_ascii=True)

        target_key = 'device'

        # Modify the cluster data if member of cluster
        if device_data['cluster'] is not None:
            target_key = 'cluster'

            changed = False

            with path_to_clusters_file.open() as clusters_input:
                clusters = json.load(clusters_input)
                cluster_index = next(idx for idx, cluster in enumerate(
                    clusters['data']) if cluster['id'] == device_data['cluster'])

                if device_data['gateway'] not in clusters['data'][cluster_index]['gateways']:
                    clusters['data'][cluster_index]['gateways'].append(
                        device_data['gateway'])
                    changed = True

            if changed:
                with path_to_clusters_file.open(mode='w') as clusters_output:
                    json.dump(clusters, clusters_output, indent=4,
                              skipkeys=True, sort_keys=True, ensure_ascii=True)

        # Modify the gateway data
        with path_to_gateways_file.open() as gateway_input:
            gateways = json.load(gateway_input)
            gateway_index = next(idx for idx, gateway in enumerate(
                gateways['data']) if gateway['id'] == device_data['gateway'])

            appended_data = device_data['cluster'] if device_data['cluster'] is not None else device_data['id']

            gateways['data'][gateway_index]['list'][target_key].append(
                appended_data)

        with path_to_gateways_file.open(mode='w') as gateway_output:
            json.dump(gateways, gateway_output, indent=4,
                      skipkeys=True, sort_keys=True, ensure_ascii=True)

    except:
        return False
    else:
        return True


def parse_lines(lines):
    connect_arr = []
    stats_arr = []
    results = {}
    failed_gateways = {
        'conn_failed': [],
        'rejected': [],
        'lost': []
    }

    for line in lines:
        if line[0] == 'CONNECT':
            if line[2] == 'success':
                connect_arr.append(line)
            elif line[2] == 'failed':
                failed_gateways['conn_failed'].append(line[2])
        elif line[0] == 'RESULT':
            if line[4] in ['copy', 'overwrite', 'skipped']:
                if line[1] not in results:
                    results[line[1]] = []
                result[line[1]].append(line)
            elif line[4] in ['rejected', 'lost']:
                if line[1] in failed_gateways[line[4]]:
                    pass
                else:
                    failed_gateways[line[4]].append(line[1])
        elif line[0] == 'STATS':
            if line[1] in failed_gateways['conn_failed']:
                pass
            else:
                stats_arr.append(line)

    return {
        'CONNECT': connect_arr,
        'RESULT': results,
        'STATUS': stats_arr,
        'FAILED': failed_gateways,
    }

"""
Before running, the file(s) to be sent must be prepared in a directory with this structure:
(base_dir)/(device or cluster)/(device or cluster ID)

For example, with the default base_dir (./data/) and target cluster ID of "example_cluster":
./data/cluster/example_cluster
"""
def run_uftp_server(target_id, is_cluster=False, retries=2):
    status_response = {}
    status_response['status'] = ''
    status_response['message'] = ''
    
    try:
        try:
            proc_name = 'uftp.exe'
            uftp_server_check = next(
                proc for proc in psutil.process_iter() if proc.name() == proc_name)

            print('Another UFTP Server Instance is currently running!')
            print('UFTP Server Instance Information:')
            print(uftp_server_check.as_dict())

            status_response['status'] = 'instance_running'
            status_response['message'] = 'Currently, the system can only be used in single user mode'
            status_response['instance_info'] = uftp_server_check.as_dict()

        except StopIteration:
            status_response['session_info'] = []
            attempts = 0

            all_good = None

            while attempts <= retries:
                session_info = {}
                status_data = {}

                gateway_ids = []
                target_dir = ''

                if is_cluster is True:
                    with path_to_clusters_file.open() as clusters_file:
                        clusters = json.load(clusters_file)
                        gateway_ids = next(cluster['gateways'].copy() for cluster in clusters['data'] if cluster['id'] == target_id)

                    target_dir = base_dir / 'cluster' / str(target_id)
                elif is_cluster is False:
                    with path_to_devices_file.open() as devices_file:
                        devices = json.load(devices_file)
                        gateway_ids = [
                            next(device['gateway'] for device in devices['data'] if device['id'] == target_id)]

                    target_dir = base_dir / 'devices' / str(target_id)

                if target_dir.exists() is False:
                    break

                session_info['gateways_list'] = gateway_ids.copy()
                session_info['target_dir'] = str(target_dir)

                host_list = ','.join(gateway_id for gateway_id in gateway_ids)

                if is_cluster is True:
                    host_list = '"' + host_list + '"'

                with psutil.Popen(uftp_server_cmd + [host_list, str(target_dir)]) as uftp_server:
                    return_code = uftp_server.wait(timeout=process_timeout)

                message = ''

                if return_code in [2, 3, 4, 5, 6, 9]:
                    message = 'An error occurred!'
                elif return_code in [7, 8]:
                    message = 'No Clients responded!'
                elif return_code in [1, 10]:
                    message = 'Session Complete!'

                    with status_file.open() as f:
                        lines = [line.rstrip().split(';') for line in f]

                    status_data = parse_lines(lines)

                    # Check for any failure in this session
                    all_good = len(
                        [val for val in status_data['FAILED'].values() if len(val) > 0]) == 0
                else:
                    message = 'Something wrong occured!'

                print(message)
                session_info['message'] = message
                session_info['return_code'] = return_code

                status_response['session_info'].append(
                    {**session_info, 'status_file': status_data})

                if all_good is True:
                    break
                else:
                    attempts += 1

            if all_good is True:
                status_response['status'] = 'success'
                status_response['message'] = 'Updates successfully sent to gateway!'
            elif all_good is False:
                status_response['status'] = 'failed'
            elif all_good is None:
                status_response['status'] = 'target_dir_not_found'

    except TimeoutExpired:
        # If UFTP Server runs longer than the defined timeout value
        print('UFTP Server Timed Out! Re-tune the parameters or try again')
        status_response['status'] = 'timeout'
        status_response['message'] = 'TimedOut when sending files to gateways'

    except StopIteration:
        keyword = 'cluster' if is_cluster is True else 'device'
        msg = 'No {} with that ID exists'.format(keyword)
        print(msg)
        status_response['status'] = 'missing_' + keyword
        status_response['message'] = msg

    except:
        print('An error occurred!')
        raise
    finally:
        # Deletes the status file so that the next session starts with a clean file
        if status_file.exists() is True:
            status_file.unlink()

        return status_response

# End of Internal Functions

# Client facing endpoints
@app.route('/list/devices/', methods=['GET'])
def get_devices():
    with path_to_devices_file.open() as devices_file:
        devices = json.load(devices_file)
        return jsonify(devices)


@app.route('/list/clusters/', methods=['GET'])
def get_clusters():
    with path_to_clusters_file.open() as clusters_file:
        clusters = json.load(clusters_file)
        return jsonify(clusters)


@app.route('/list/free_devices/', methods=['GET'])
def get_free_devices():
    with path_to_devices_file.open() as devices_file:
        devices = json.load(devices_file)
        free_devices = [device for device in devices['data']
                        if device['cluster'] is None]
        return jsonify({'data': free_devices})


@app.route('/update/device/', methods=['POST'])
def start_update_device():
    status_response = {}
    status_response['status'] = ''
    status_response['message'] = ''

    id_schema = Schema({Required('id'): id_validator})

    try:
        target_id = id_schema(request.json)['id']

        if check_item_exists(target_id) is not True:
            raise StopIteration

        status_response = run_uftp_server(target_id)

        if status_response['status'] == 'success':
            # Publish "update" instruction via MQTT to instruct gateways to start update process
            with path_to_devices_file.open() as devices_file:
                devices = json.load(devices_file)
                target_device = next(device for device in devices['data'] if device['id'] == target_id)

            if target_device['cluster'] is None:
                mqtt.publish(global_topic, 'update|device|' + target_id, qos=2)
            else:
                mqtt.publish(cluster_topic + '/' + target_device['cluster'], 'update|device|' + target_id, qos=2)

    except StopIteration:
        status_response['status'] = 'missing_device'
        status_response['message'] = 'No Device with that ID exists!'
    except MultipleInvalid:
        abort(400)
    finally:
        return jsonify(status_response)


@app.route('/update/cluster/', methods=['POST'])
def start_update_cluster():
    status_response = {}
    status_response['status'] = ''
    status_response['message'] = ''

    id_schema = Schema({Required('id'): id_validator})

    try:
        target_id = id_schema(request.json)['id']

        if check_item_exists(target_id, item_type='cluster') is not True:
            raise StopIteration

        status_response = run_uftp_server(target_id, is_cluster=True)

        if status_response['status'] == 'success':
            # Publish "update" instruction via MQTT to instruct gateways to start update process
            mqtt.publish(cluster_topic + '/' + target_id, 'update|cluster|' + target_id, qos=2)

    except StopIteration:
        status_response['status'] = 'missing_cluster'
        status_response['message'] = 'No Cluster with that ID exists!'
    except MultipleInvalid:
        abort(400)
    finally:
        return jsonify(status_response)


@app.route('/new/device/', methods=['POST'])
def add_new_device():
    status_response = {}
    status_response['status'] = ''
    status_response['message'] = ''

    id_schema = Schema({Required('id'): id_validator})

    try:
        new_device_id = id_schema(request.json)['id']

        if check_item_exists(new_device_id):
            status_response['status'] = 'exists'
            status_response['message'] = 'Device with that ID already exists!'
        else:
            with path_to_devices_file.open() as devices_file:
                devices = json.load(devices_file)
                new_device_data = {
                    'id': new_device_id,
                    'cluster': None,
                    'type': None,
                    'gateway': None
                }
                devices['data'].append(new_device_data)

            with path_to_devices_file.open(mode='w') as devices_file:
                json.dump(devices, devices_file, indent=4,
                          skipkeys=True, sort_keys=True, ensure_ascii=True)

            status_response['status'] = 'success'
            status_response['message'] = 'New device successfully created!'

    except OSError:
        status_response['status'] = 'error'
        status_response['message'] = 'Server Side Error Occurred!'
    except MultipleInvalid:
        abort(400)
    finally:
        return jsonify(status_response)


@app.route('/new/cluster/', methods=['POST'])
def add_new_cluster():
    status_response = {}
    status_response['status'] = ''
    status_response['message'] = ''

    id_schema = Schema({Required('id'): id_validator})

    try:
        new_cluster_id = id_schema(request.json)['id']

        if check_item_exists(new_cluster_id, item_type='cluster'):
            status_response['status'] = 'exists'
            status_response['message'] = 'Cluster with that ID already exists!'
        else:
            with path_to_clusters_file.open() as clusters_file:
                clusters = json.load(clusters_file)
                new_cluster_data = {
                    'id': new_cluster_id,
                    'type': None,
                    'devices': [],
                    'gateways': []
                }

                clusters['data'].append(new_cluster_data)

            with path_to_clusters_file.open(mode='w') as clusters_file:
                json.dump(clusters, clusters_file, indent=4,
                          skipkeys=True, sort_keys=True, ensure_ascii=True)

            status_response['status'] = 'success'
            status_response['message'] = 'New cluster successfully created!'

    except OSError:
        status_response['status'] = 'error'
        status_response['message'] = 'Server Side Error Occurred!'
    except MultipleInvalid:
        abort(400)
    finally:
        return jsonify(status_response)


@app.route('/delete/device/', methods=['POST'])
def delete_device():
    status_response = {}
    status_response['status'] = ''
    status_response['message'] = ''

    json_validator = Schema({Required('id'): id_validator})

    try:
        target_id = json_validator(request.json)['id']

        if not check_item_exists(target_id):
            status_response['status'] = 'missing_device'
            status_response['message'] = 'No device with that ID exists!'
        else:
            with path_to_devices_file.open() as devices_file:
                devices = json.load(devices_file)
                target_index = next(
                    idx for idx, device in enumerate(devices['data']) if device['id'] == target_id)
                target_device = devices['data'].pop(target_index)

            # De-couple device from cluster
            if target_device['cluster'] is not None:
                with path_to_clusters_file.open() as clusters_file:
                    clusters = json.load(clusters_file)
                    cluster_index = next(idx for idx, cluster in enumerate(
                        clusters['data']) if cluster['id'] == target_device['cluster'])
                    clusters['data'][cluster_index]['devices'].remove(
                        target_device['id'])

                with path_to_clusters_file.open(mode='w') as clusters_file:
                    json.dump(clusters, clusters_file, indent=4,
                              skipkeys=True, sort_keys=True, ensure_ascii=True)

            with path_to_devices_file.open(mode='w') as devices_file:
                json.dump(devices, devices_file, indent=4,
                          skipkeys=True, sort_keys=True, ensure_ascii=True)

            status_response['status'] = 'success'
            status_response['message'] = 'Device deleted successfully!'
    except OSError:
        status_response['status'] = 'error'
        status_response['message'] = 'Server Side Error Occurred!'
    except MultipleInvalid:
        abort(400)
    finally:
        return jsonify(status_response)


@app.route('/delete/cluster/', methods=['POST'])
def delete_cluster():
    status_response = {}
    status_response['status'] = ''
    status_response['message'] = ''

    json_validator = Schema({Required('id'): id_validator})

    try:
        target_id = json_validator(request.json)['id']

        if not check_item_exists(target_id, item_type='cluster'):
            status_response['status'] = 'missing_cluster'
            status_response['message'] = 'No cluster with that ID exists!'
        else:
            with path_to_clusters_file.open() as clusters_file:
                clusters = json.load(clusters_file)
                target_index = next(idx for idx, cluster in enumerate(clusters['data']) if cluster['id'] == target_id)
                target_cluster = clusters['data'].pop(target_index)

            if len(target_cluster['devices']) > 0:
                with path_to_devices_file.open() as devices_file:
                    devices = json.load(devices_file)

                device_indices = [idx for idx, device in enumerate(devices['data']) if device['id'] in target_cluster['devices']]

                for device_index in device_indices:
                    del devices['data'][device_index]

                with path_to_devices_file.open(mode='w') as devices_file:
                    json.dump(devices, devices_file, indent=4,
                        skipkeys=True, sort_keys=True, ensure_ascii=True)

            with path_to_clusters_file.open() as clusters_file:
                json.dump(devices, clusters_file, indent=4,
                        skipkeys=True, sort_keys=True, ensure_ascii=True)

            status_response['status'] = 'success'
            status_response['message'] = 'Cluster deleted (recusively) successfully!'

    except OSError:
        status_response['status'] = 'error'
        status_response['message'] = 'Server Side Error Occurred!'
    except MultipleInvalid:
        abort(400)
    finally:
        return jsonify(status_response)


@app.route('/register/device/', methods=['PATCH'])
def register_device_to_cluster():
    json_validator = Schema({
        Required('device_id'): id_validator,
        Required('cluster_id'): id_validator
    })

    status_response = {}
    status_response['status'] = ''
    status_response['message'] = ''

    try:
        data = json_validator(request.json)

        if check_device_membership(data['device_id']) is not None:
            status_response['status'] = 'membership_exists'
            status_response['message'] = 'Device already a member of a cluster!'
        elif check_item_exists(data['device_id']) is not True:
            status_response['status'] = 'missing_device'
            status_response['message'] = 'No Device with that ID exists!'
        elif check_item_exists(data['cluster_id'], item_type='cluster') is not True:
            status_response['status'] = 'missing_cluster'
            status_response['message'] = 'No Cluster with that ID exists!'
        else:
            # Modify Cluster data
            with path_to_clusters_file.open() as clusters_file:
                clusters = json.load(clusters_file)
                target_cluster = next(idx for idx, cluster in enumerate(
                    clusters['data']) if cluster['id'] == data['cluster_id'])
                clusters['data'][target_cluster]['devices'].append(
                    data['device_id'])

            with path_to_clusters_file.open(mode='w') as clusters_file:
                json.dump(clusters, clusters_file, indent=4, skipkeys=True,
                          sort_keys=True, ensure_ascii=True)

            # Modify Device data
            with path_to_devices_file.open() as devices_file:
                devices = json.load(devices_file)
                target_device = next(
                    idx for idx, device in enumerate(devices['data']) if device['id'] == data['device_id'])
                devices['data'][target_device]['cluster'] = data['cluster_id']

            with path_to_devices_file.open(mode='w') as devices_file:
                json.dump(devices, devices_file, indent=4, skipkeys=True,
                          sort_keys=True, ensure_ascii=True)

            status_response['status'] = 'success'
            status_response['message'] = 'Device registered to cluster successfully!'
    except MultipleInvalid:
        abort(400)
    finally:
        return jsonify(status_response)

# End of client facing endpoints


# Controller/Gateway functions
@app.route('/init/device/', methods=['PUT'])
def initialize_device():
    strict_device_validator = Schema({
        Required('id'): id_validator,
        Required('type'): Coerce(str),
        Required('cluster', default=None): Any(Maybe(str), id_validator),
        Required('gateway'): All(Coerce(str), Match(r'^0x[0-9A-F]{8}$'))
    })

    status_response = {}
    status_response['status'] = ''
    status_response['message'] = ''

    try:
        device_data = strict_device_validator(request.json)

        if check_item_exists(device_data['id']) is not True:
            status_response['status'] = 'missing_device'
            status_response['message'] = 'No Device with that ID exists!'
        elif check_item_exists(device_data['gateway'], item_type='gateway') is not True:
            status_response['status'] = 'missing_gateway'
            status_response['message'] = 'No Gateway with that ID exists!'
        elif device_data['cluster'] is not None and check_item_exists(device_data['cluster'], item_type='cluster') is not True:
            status_response['status'] = 'missing_cluster'
            status_response['message'] = 'No Cluster with that ID exists!'
        elif check_device_membership(device_data['id']) != device_data['cluster']:
            status_response['status'] = 'incorrect_cluster'
            status_response['message'] = 'Incorrect cluster defined!'
        else:
            if register_to_gateway(device_data) is True:
                status_response['status'] = 'success'
                status_response['message'] = 'Device initialized successfully!'
            else:
                status_response['status'] = 'error'
                status_response['message'] = 'Error while registering device to gateway!'

    except MultipleInvalid:
        abort(400)
    finally:
        return jsonify(status_response)


@app.route('/init/gateway/', methods=['GET'])
def initialize_gateway():
    status_response = {}
    status_response['status'] = ''
    status_response['message'] = ''

    try:
        status_response['status'] = 'success'
        status_response['message'] = 'Gateway initialized successfully!'
        status_response['gateway_uid'] = generate_gateway_uid()
        status_response['mqtt_topic'] = global_topic
        status_response['mqtt_broker'] = mqtt_broker
        status_response['end_device_multicast_addr'] = end_device_multicast_addr
        status_response['max_log_size'] = max_log_size
        status_response['max_log_count'] = max_log_count
    except:
        status_response['status'] = 'error'
        status_response['message'] = 'Error while initializing gateway!'
    finally:
        return jsonify(status_response)

# End of Controller/Gateway functions


# MQTT Functions

@mqtt.on_connect()
def handle_connect(client, userdata, flags, rc):    
    if rc == 0:
        print('Successfully connected to ' + mqtt_broker)
        mqtt.subscribe(global_topic, qos=2)
        mqtt.subscribe(cluster_topic, qos=2)

    elif rc == 1:
        print('Incorrect Protocol Version detected when connecting to ' + mqtt_broker)
    elif rc == 2:
        print('Invalid Client ID detected when connecting to ' + mqtt_broker)
    elif rc == 3:
        print('MQTT Server/Broker is unavailable when connecting to ' + mqtt_broker)
    elif rc == 4:
        print('Bad Username/Password detected when connecting to ' + mqtt_broker)
    elif rc == 5:
        print('Failed to Authorize when connecting to ' + mqtt_broker)
    else:
        print('Invalid Return Code (' + str(rc) + ') when connecting to ' + mqtt_broker)

@mqtt.on_message()
def handle_message(client, userdata, msg):
    print("Message Received from topic " + str(
        msg.topic) + ' : ' + str(msg.payload.decode()))


# End of MQTT Functions

# CLI Entry point
if __name__ == '__main__':
    init_dirs()
    init_files()
    app.run()
