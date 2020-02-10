from flask import Flask, request, jsonify
from flask_mqtt import Mqtt

from voluptuous import Schema, Required, All, Any, Length, Coerce, Maybe, Match, MultipleInvalid
import json
import random

from pathlib import Path

app = Flask(__name__)

global_topic = 'ota/control'

curr_dir = Path(__file__).parent.absolute()

path_to_devices_file =  curr_dir / 'data' / 'devices.json'
path_to_clusters_file = curr_dir / 'data' / 'clusters.json'
path_to_gateways_file = curr_dir / 'data' / 'gateways.json'

path_to_uftp_server_exe = curr_dir / 'uftp' / 'uftp.exe'
status_file = curr_dir / 'uftp' / 'status.txt'
base_dir = curr_dir / 'data'

server_uid = '0xABCDABCD'
transfer_rate = '1024'  # in Kbps

# Still need to append client list
uftp_server_commands = [str(path_to_uftp_server_exe), 
                        '-l', '-z',
                        '-U', server_uid, 
                        '-t', '3', 
                        '-R', transfer_rate, 
                        '-S', str(status_file), 
                        '-E', str(base_dir), 
                        '-H']


# use the free broker from HIVEMQ
app.config['MQTT_CLIENT_ID'] = 'main_server'
app.config['MQTT_BROKER_URL'] = 'broker.hivemq.com'
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
    with path_to_gateways_file.open() as json_input:
        gateways = json.load(json_input)

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

    with path_to_gateways_file.open(mode='w') as json_output:
        json.dump(gateways, json_output, indent=4, ensure_ascii=True)

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
    try:
        with path_to_devices_file.open() as json_file:
            devices = json.load(json_file)['data']
            device_membership = next(
                device for device in devices if device['id'] == device_id)

    except:
        return None
    else:
        return device_membership['cluster']


def init_files():
    init_data = {"data": []}
    files = [path_to_devices_file,
             path_to_clusters_file, path_to_gateways_file]

    for file in files:
        if not file.exists():
            with file.open(mode='w') as json_file:
                json.dump(init_data, json_file, indent=4, ensure_ascii=True)


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


def run_uftp_server(id, is_cluster=False):
    # TODO: Might need to "randomize" some parameters later to enable many-users-at-once
    # Check for existing server process

    # Prepare "hostlist" to send to

    # Run the server process with the prepared commands

    # Check the status file for the result
    # Compare the status file with the known parameters (target devices, amount of files sent, etc)

    # if any failure is present, repeat the process
    # TODO: Try to mimic the "RESTART MODE" of the UFTP for efficiency
    # e.g. only send missing files to required clients, but still in SYNC mode
    # For every "retry", refresh the status file for easy parsing

    # After the transfer process is determined to be successful (or after a certain number of retries failed)
    # return False if failed
    # Publish "command" to MQTT so that gateways know when to "go update the end devices"
    # Return True
    pass

# End of Internal Functions

# Client facing endpoints
@app.route('/list/devices/', methods=['GET'])
def get_devices():
    with path_to_devices_file.open() as json_file:
        devices = json.load(json_file)
        return jsonify(devices)


@app.route('/list/clusters/', methods=['GET'])
def get_clusters():
    with path_to_clusters_file.open() as json_file:
        clusters = json.load(json_file)
        return jsonify(clusters)


@app.route('/list/free_devices/', methods=['GET'])
def get_free_devices():
    with path_to_devices_file.open() as json_file:
        devices = json.load(json_file)
        free_devices = [device for device in devices['data']
                        if device['cluster'] is None]
        return jsonify(free_devices)

# TODO: Access file system and call UFTP server
@app.route('/update/device/', methods=['POST'])
def start_update_device():
    pass


@app.route('/update/cluster/', methods=['POST'])
def start_update_cluster():
    pass


@app.route('/new/device/', methods=['POST'])
def add_new_device():
    status_response = {}
    status_response['status'] = ''

    id_schema = Schema({Required('id'): id_validator})

    try:
        new_device_id = id_schema(request.json)['id']

        if check_item_exists(new_device_id):
            status_response['status'] = 'exists'
        else:
            with path_to_devices_file.open()as json_input:
                devices = json.load(json_input)
                new_device_data = {
                    'id': new_device_id,
                    'cluster': None,
                    'type': None,
                    'gateway': None
                }
                devices['data'].append(new_device_data)

            with path_to_devices_file.open(mode='w') as json_output:
                json.dump(devices, json_output, indent=4,
                          skipkeys=True, sort_keys=True, ensure_ascii=True)

            status_response['status'] = 'success'

    except OSError:
        status_response['status'] = 'error'
        status_response['message'] = 'Server Side Error Occurred!'
    except MultipleInvalid:
        raise BadRequest
    finally:
        return jsonify(status_response)


@app.route('/new/cluster/', methods=['POST'])
def add_new_cluster():
    status_response = {}
    status_response['status'] = ''

    id_schema = Schema({Required('id'): id_validator})

    try:
        new_cluster_id = id_schema(request.json)['id']

        if check_item_exists(new_cluster_id, item_type='cluster'):
            status_response['status'] = 'exists'
        else:
            with path_to_clusters_file.open() as json_input:
                clusters = json.load(json_input)
                new_cluster_data = {
                    'id': new_cluster_id,
                    'type': None,
                    'devices': [],
                    'gateways': []
                }

                clusters['data'].append(new_cluster_data)

            with path_to_clusters_file.open(mode='w') as json_output:
                json.dump(clusters, json_output, indent=4,
                          skipkeys=True, sort_keys=True, ensure_ascii=True)

            status_response['status'] = 'success'

    except OSError:
        status_response['status'] = 'error'
        status_response['message'] = 'Server Side Error Occurred!'
    except MultipleInvalid:
        raise BadRequest
    finally:
        return jsonify(status_response)


@app.route('/delete/device/', methods=['POST'])
def delete_device():
    status_response = {}
    status_response['status'] = ''

    json_validator = Schema({Required('id'): id_validator})

    try:
        data = json_validator(request.json)

        if not check_item_exists(data['id']):
            status_response['status'] = 'missing_device'
            status_response['message'] = 'No device with that ID'
        else:
            with path_to_devices_file.open() as json_input:
                devices = json.load(json_input)
                target_index = next(
                    idx for idx, device in enumerate(devices['data']) if device['id'] == data['id'])
                target_device = devices['data'].pop(target_index)

            if target_device['cluster'] is not None:
                with path_to_clusters_file.open() as json_input:
                    clusters = json.load(json_input)
                    cluster_index = next(idx for idx, cluster in enumerate(
                        clusters['data']) if cluster['id'] == target_device['cluster'])
                    clusters['data'][cluster_index]['devices'].remove(
                        target_device['id'])

                with path_to_clusters_file.open(mode='w') as json_output:
                    json.dump(clusters, json_output, indent=4,
                              skipkeys=True, sort_keys=True, ensure_ascii=True)

            with path_to_devices_file.open(mode='w') as json_output:
                json.dump(devices, json_output, indent=4,
                          skipkeys=True, sort_keys=True, ensure_ascii=True)

            status_response['status'] = 'success'
            status_response['message'] = 'Successfully deleted device ' + target_device['id']
    except OSError:
        status_response['status'] = 'error'
        status_response['message'] = 'Server Side Error Occurred!'
    except MultipleInvalid:
        raise BadRequest
    finally:
        return jsonify(status_response)


@app.route('/delete/cluster/', methods=['POST'])
def delete_cluster():
    pass


@app.route('/register/device/', methods=['PATCH'])
def register_device_to_cluster():
    json_validator = Schema({
        Required('device_id'): id_validator,
        Required('cluster_id'): id_validator
    })

    status_response = {}
    status_response['status'] = ''

    try:
        data = json_validator(request.json)

        if check_device_membership(data['device_id']) is not None:
            status_response['status'] = 'membership'
        elif not check_item_exists(data['device_id']):
            status_response['status'] = 'missing_device'
        elif not check_item_exists(data['cluster_id'], item_type='cluster'):
            status_response['status'] = 'missing_cluster'
        else:
            # Modify Cluster data
            with path_to_clusters_file.open() as json_input:
                clusters = json.load(json_input)
                target_cluster = next(idx for idx, cluster in enumerate(
                    clusters['data']) if cluster['id'] == data['cluster_id'])
                clusters['data'][target_cluster]['devices'].append(
                    data['device_id'])

            with path_to_clusters_file.open(mode='w') as json_output:
                json.dump(clusters, json_output, indent=4, skipkeys=True,
                          sort_keys=True, ensure_ascii=True)

            # Modify Device data
            with path_to_devices_file.open() as json_input:
                devices = json.load(json_input)
                target_device = next(
                    idx for idx, device in enumerate(devices['data']) if device['id'] == data['device_id'])
                devices['data'][target_device]['cluster'] = data['cluster_id']

            with path_to_devices_file.open(mode='w') as json_output:
                json.dump(devices, json_output, indent=4, skipkeys=True,
                          sort_keys=True, ensure_ascii=True)

            status_response['status'] = 'success'

    except MultipleInvalid:
        raise BadRequest
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

    try:
        device_data = strict_device_validator(request.json)

        if check_item_exists(device_data['id']) is not True:
            status_response['status'] = 'unknown'
        elif check_item_exists(device_data['gateway'], item_type='gateway') is not True:
            status_response['status'] = 'missing_gateway'
        elif device_data['cluster'] is not None and check_item_exists(device_data['cluster'], item_type='cluster') is not True:
            status_response['status'] = 'missing_cluster'
        elif check_device_membership(device_data['id']) == device_data['cluster']:
            status_response['status'] = 'incorrect_cluster'
        else:
            status_response['status'] = 'success' if register_to_gateway(device_data) is True else 'error'

    except MultipleInvalid:
        raise BadRequest
    finally:
        return jsonify(status_response)


@app.route('/init/gateway/', methods=['GET'])
def initialize_gateway():
    status_response = {}
    status_response['status'] = ''

    try:
        new_gateway_uid = generate_gateway_uid()
        status_response['status'] = 'success'
        status_response['new_gateway_uid'] = new_gateway_uid
    except:
        status_response['status'] = 'error'
    finally:
        return jsonify(status_response)

# End of Controller/Gateway functions


# MQTT Functions

@mqtt.on_connect()
def handle_connect(client, userdata, flags, rc):
    print("Connected with return code {}".format(rc))
    mqtt.subscribe(global_topic, qos=1)


@mqtt.on_message()
def handle_message(client, userdata, message):
    # TODO: Differentiate logic here based on the messages
    print("Message Received from topic {} : {}".format(
        message.topic, message.payload.decode()))

# End of MQTT Functions

if __name__ == '__main__':
    init_files()
    app.run()
