from flask import Flask, request, jsonify
from flask_mqtt import Mqtt

from voluptuous import Schema, Required, All, Any, Length, Coerce, Maybe, Match, MultipleInvalid
import json
import random

from pathlib import Path

app = Flask(__name__)

path_to_devices_file = './data/devices.json'
path_to_clusters_file = './data/clusters.json'
path_to_gateways = './data/gateways.json'

server_uid = '0x12349876'

uftp_server_commands = ['./uftp/uftp.exe', '-q', '-f', '-z', '-U', server_uid, ]

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
    Required('list', default=list): list
})

# Client facing endpoints
@app.route('/list/devices/', methods=['GET'])
def get_devices():
    with open(path_to_devices_file, 'r') as json_file:
        devices = json.load(json_file)
        return jsonify(devices)


@app.route('/list/clusters/', methods=['GET'])
def get_clusters():
    with open(path_to_clusters_file, 'r') as json_file:
        clusters = json.load(json_file)
        return jsonify(clusters)


@app.route('/list/free_devices/', methods=['GET'])
def get_free_devices():
    with open(path_to_devices_file, 'r') as json_file:
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

    try:
        new_device_data = device_schema(request.json)

        if check_item_exists(new_device_data['id']):
            status_response['status'] = 'exists'
        else:
            with open(path_to_devices_file, 'r') as json_input:
                devices = json.load(json_input)
                devices['data'].append(new_device_data)

            with open(path_to_devices_file, 'w') as json_output:
                json.dump(devices, json_output, indent=4, skipkeys=True, sort_keys=True, ensure_ascii=True)

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

    try:
        new_cluster_data = cluster_schema(request.json)

        if check_item_exists(new_cluster_data['id'], check_cluster=True):
            status_response['status'] = 'exists'
        else:
            with open(path_to_clusters_file, 'r') as json_input:
                clusters = json.load(json_input)
                clusters['data'].append(new_cluster_data)

            with open(path_to_clusters_file, 'w') as json_output:
                json.dump(clusters, json_output, indent=4, skipkeys=True, sort_keys=True, ensure_ascii=True)

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

    json_validator = Schema({Required('id') : id_validator})

    try:
        data = json_validator(request.json)

        if not check_item_exists(data['id']):
            status_response['status'] = 'missing_device'
        else:
            with open(path_to_devices_file, 'r') as json_input:
                devices = json.load(json_input)
                target_index = next(
                    idx for idx, device in enumerate(devices['data']) if device['id'] == data['id'])
                target_device = devices['data'].pop(target_index)

            if target_device['cluster'] is not None:
                with open(path_to_clusters_file, 'r') as json_input:
                    clusters =  json.load(json_input)
                    cluster_index = next(idx for idx, cluster in enumerate(clusters['data']) if cluster['id'] == target_device['cluster'])
                    clusters['data'][cluster_index]['list'].remove(target_device['id'])

                with open(path_to_clusters_file, 'w') as json_output:
                    json.dump(clusters, json_output, indent=4, skipkeys=True, sort_keys=True, ensure_ascii=True)

            with open(path_to_devices_file, 'w') as json_output:
                json.dump(devices, json_output, indent=4, skipkeys=True, sort_keys=True, ensure_ascii=True)
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
        Required('device_id') : id_validator,
        Required('cluster_id') : id_validator
    })

    status_response = {}
    status_response['status'] = ''

    try:
        data = json_validator(request.json)

        if check_device_membership(data['device_id']) is not None:
            status_response['status'] = 'membership'
        elif not check_item_exists(data['device_id']):
            status_response['status'] = 'missing_device'
        elif not check_item_exists(data['cluster_id'], check_cluster=True):
            status_response['status'] = 'missing_cluster'
        else:
            # Modify Cluster data
            with open(path_to_clusters_file, 'r') as json_input:
                clusters = json.load(json_input)
                target_cluster = next(idx for idx, cluster in enumerate(clusters['data']) if cluster['id'] == data['cluster_id'])
                clusters['data'][target_cluster]['list'].append(
                    data['device_id'])

            with open(path_to_clusters_file, 'w') as json_output:
                json.dump(clusters, json_output, indent=4, skipkeys=True,
                          sort_keys=True, ensure_ascii=True)

            # Modify Device data
            with open(path_to_devices_file, 'r') as json_input:
                devices = json.load(json_input)
                target_device = next(
                    idx for idx, device in enumerate(devices['data']) if device['id'] == data['device_id'])
                devices['data'][target_device]['cluster'] = data['cluster_id']

            with open(path_to_devices_file, 'w') as json_output:
                json.dump(devices, json_output, indent=4, skipkeys=True,
                          sort_keys=True, ensure_ascii=True)

            status_response['status'] = 'success'

    except MultipleInvalid:
        raise BadRequest
    finally:
        return jsonify(status_response)

# End of client facing endpoints

# Controller/Gateway functions
# TODO: Validate JSON Format
@app.route('/init/device/', methods=['PUT'])
def initialize_device():
    device_data = request.json

    if check_item_exists(device_data['id']) is not True:
        # This device is unknown
        pass

    if device_data['cluster'] is None:
        # Is this device not part of a cluster?
        if check_device_membership(device_data['id']) is None:
            # This IS a solitary device
            pass
        else:
            # Lies, this device is part of a cluster!
            pass
    else:
        # Does this cluster exists?
        if check_item_exists(device_data['cluster'], check_cluster=True) is not True:
            pass

        # Check the device membership
        if check_device_membership(device_data['id']) == device_data['cluster']:
            # This IS part of the correct cluster
            pass
        else:
            # It is a member of a cluster, but you're wrong
            pass

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

# Internal Functions
def generate_gateway_uid():
    with open(path_to_gateways_file, 'r') as json_input:
        gateways = json.load(json_input)

    while True:
        random_hexa_uid = '0x%08X' % random.randrange(16**8)
        gateway_exists = random_hexa_uid in (gateway['uid'] for gateway in gateways['data'])

        if gateway_exists is False:
            break

    new_gateway = {
        "id" : random_hexa_uid,
        "list" : {
            "cluster":[],
            "device":[],
        }
    }

    gateways['data'].append(new_gateway)

    with open(path_to_gateways_file, 'w') as json_output:
        json.dump(gateways, json_output, indent=4, ensure_ascii=True)

    return random_hexa_uid

def check_item_exists(item_id, check_cluster=False):
    target_file = path_to_devices_file

    if check_cluster:
        target_file = path_to_clusters_file

    with open(target_file, 'r') as json_file:
        items = json.load(json_file)['data']
        item_exists = [item for item in items if item['id'] == item_id]

    return len(item_exists) > 0

def check_device_membership(device_id):
    with open(path_to_devices_file, 'r') as json_file:
        devices = json.load(json_file)['data']
        device_membership = [
            device for device in devices if device['id'] == device_id]

    return device_membership[0]['cluster']

def init_files():
    init_data = {"data": []}
    files = [path_to_devices_file, path_to_clusters_file]

    for filename in files:
        file_path = Path(filename)

        if not file_path.exists():
            with open(filename, 'w') as json_file:
                json.dump(init_data, json_file, indent=4, ensure_ascii=True)

# End of Internal Functions


# MQTT Functions
global_topic = 'ota/control'

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
