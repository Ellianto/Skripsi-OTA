import random

from flask import abort, jsonify, request
from voluptuous import MultipleInvalid

from server import app, constants
from server.internal_handlers import file_io, helpers


def generate_gateway_uid():
    gateways = file_io.read_gateways()

    attempts = 0

    for attempts in range(10000000):
        attempts += 1
        random_hexa_uid = '0x%08X' % random.randrange(16**8)
        gateway_exists = next((
            gateway['id'] for gateway in gateways['data'] if gateway['id'] == random_hexa_uid), None)

        if gateway_exists is None:
            break

    return random_hexa_uid


def register_to_gateway(device_data):
    success = False

    try:
        # Modify Devices file
        devices = file_io.read_devices()
        device_index = helpers.find_index(devices, device_data['id'])
        devices['data'][device_index] = device_data
        file_io.write_devices(devices)

        # Modify Gateway data
        gateways = file_io.read_gateways()
        gateway_index = helpers.find_index(gateways, device_data['gateway'])

        if device_data['cluster'] is not None:
            if device_data['cluster'] not in gateways['data'][gateway_index]['cluster']:
                gateways['data'][gateway_index]['cluster'].append(
                    device_data['cluster'])
                file_io.write_gateways(gateways)

            # Modify Clusters data
            clusters = file_io.read_clusters()
            cluster_index = helpers.find_index(clusters, device_data['cluster'])

            if device_data['gateway'] not in clusters['data'][cluster_index]['gateways']:
                clusters['data'][cluster_index]['gateways'].append(
                    device_data['gateway'])
                clusters['data'][cluster_index]['type'] = device_data['type']
                file_io.write_clusters(clusters)
        else:
            if device_data['id'] not in gateways['data'][gateway_index]['device']:
                gateways['data'][gateway_index]['device'].append(
                    device_data['id'])
                file_io.write_gateways(gateways)

        success = True
    finally:
        return success


# Controller/Gateway Route Handler
@app.route('/init/device/', methods=['PUT'])
def initialize_device():
    status_response = {}
    status_response['status'] = ''
    status_response['message'] = ''

    try:
        device_data = constants.json_schema.DEVICE_SCHEMA(request.json)

        device = helpers.get_device(device_data['id'])
        gateway = helpers.get_gateway(device_data['gateway'])

        device_exist = device is not None
        gateway_exist = gateway is not None
        cluster_match = device_data['cluster'] == device['cluster']

        if device_data['cluster'] is not None:
            cluster = helpers.get_cluster(device_data['cluster'])
            cluster_exist = cluster is not None
        else:
            cluster_exist = True

        if device_exist is not True:
            status_response['status'] = constants.strings.STATUS_CODE_MISSING_DEVICE
            status_response['message'] = 'No Device with that ID exists!'
        elif gateway_exist is not True:
            status_response['status'] = constants.strings.STATUS_CODE_MISSING_GATEWAY
            status_response['message'] = 'No Gateway with that ID exists!'
        elif cluster_exist is not True:
            status_response['status'] = constants.strings.STATUS_CODE_MISSING_CLUSTER
            status_response['message'] = 'No Cluster with that ID exists!'
        elif cluster_match is not True:
            status_response['status'] = constants.strings.STATUS_CODE_CLUSTER_MISMATCH
            status_response['message'] = 'Incorrect cluster defined!'
        else:
            if register_to_gateway(device_data) is True:
                status_response['status'] = constants.strings.STATUS_CODE_SUCCESS
                status_response['message'] = 'Device initialized successfully!'
            else:
                status_response['status'] = constants.strings.STATUS_CODE_FAILED
                status_response['message'] = 'Failed registering device to gateway!'

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
        status_response['status'] = constants.strings.STATUS_CODE_SUCCESS
        status_response['message'] = 'Gateway initialized successfully!'
        status_response['gateway_uid'] = generate_gateway_uid()
        status_response['mqtt_topic'] = constants.mqtt.GLOBAL_TOPIC
        status_response['mqtt_broker'] = constants.mqtt.MQTT_BROKER_URL
        status_response['end_device_multicast_addr'] = constants.uftp.END_DEVICE_MULTICAST_ADDR
        status_response['max_log_size'] = constants.uftp.MAX_LOG_SIZE
        status_response['max_log_count'] = constants.uftp.MAX_LOG_COUNT
    except:
        status_response['status'] = constants.strings.STATUS_CODE_ERROR
        status_response['message'] = 'Error while initializing gateway!'
    finally:
        return jsonify(status_response)

# End of Controller/Gateway Route Handler
