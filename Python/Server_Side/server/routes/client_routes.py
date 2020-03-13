from flask import abort, jsonify, request
from voluptuous import MultipleInvalid, Required, Schema

from server import app, constants, mqtt_client
from server.internal_handlers import file_io, helpers, uftp_handlers


@app.route('/list/devices/', methods=['GET'])
def get_devices():
    return jsonify(file_io.read_devices())


@app.route('/list/clusters/', methods=['GET'])
def get_clusters():
    return jsonify(file_io.read_clusters())


@app.route('/list/free_devices/', methods=['GET'])
def get_free_devices():
    devices = file_io.read_devices()
    return jsonify({'data': [device for device in devices['data']
                            if device['cluster'] is None]})


@app.route('/new/device/', methods=['POST'])
def add_new_device():
    status_response = {}
    status_response['status'] = ''
    status_response['message'] = ''

    id_schema = Schema({Required('id'): constants.json_schema.ID_VALIDATOR})

    try:
        new_device_id = id_schema(request.json)['id']

        if helpers.get_device(new_device_id) is not None:
            status_response['status'] = constants.strings.STATUS_CODE_DEVICE_EXISTS
            status_response['message'] = 'Device with that ID already exists!'
        else:
            new_device_data = {
                'id': new_device_id,
                'cluster': None,
                'type': None,
                'gateway': None
            }

            devices = file_io.read_devices()
            devices['data'].append(new_device_data)
            file_io.write_devices(devices)

            status_response['status'] = constants.strings.STATUS_CODE_SUCCESS
            status_response['message'] = 'New device successfully created!'
    except OSError:
        status_response['status'] = constants.strings.STATUS_CODE_ERROR
        status_response['message'] = 'Server Side Error Occurred!'
    except MultipleInvalid:
        abort(400)

    return jsonify(status_response)


@app.route('/new/cluster/', methods=['POST'])
def add_new_cluster():
    status_response = {}
    status_response['status'] = ''
    status_response['message'] = ''

    id_schema = Schema({Required('id'): constants.json_schema.ID_VALIDATOR})

    try:
        new_cluster_id = id_schema(request.json)['id']

        if helpers.get_cluster(new_cluster_id) is not None:
            status_response['status'] = constants.strings.STATUS_CODE_CLUSTER_EXISTS
            status_response['message'] = 'Cluster with that ID already exists!'
        else:
            new_cluster_data = {
                'id': new_cluster_id,
                'type': None,
                'devices': [],
                'gateways': []
            }
            
            clusters = file_io.read_clusters()
            clusters['data'].append(new_cluster_data)
            file_io.write_clusters(clusters)

            status_response['status'] = constants.strings.STATUS_CODE_SUCCESS
            status_response['message'] = 'New cluster successfully created!'
    except OSError:
        status_response['status'] = constants.strings.STATUS_CODE_ERROR
        status_response['message'] = 'Server Side Error Occurred!'
    except MultipleInvalid:
        abort(400)
    
    return jsonify(status_response)


@app.route('/update/device/', methods=['POST'])
def ota_device():
    status_response = {}
    status_response['status'] = ''
    status_response['message'] = ''

    id_schema = Schema({Required('id'): constants.json_schema.ID_VALIDATOR})

    try:
        device_id = id_schema(request.json)['id']
        target_device = helpers.get_device(device_id)

        if target_device is None:
            status_response['status'] = constants.strings.STATUS_CODE_MISSING_DEVICE
            status_response['message'] = 'No Device with that ID exists!'
        elif target_device['type'] is None:
            status_response['status'] = constants.strings.STATUS_CODE_UNINITIALIZED
            status_response['message'] = 'Device has not been initialized!'
        else:
            status_response = uftp_handlers.distribute_updated_code(target_device['id'])

            if status_response['status'] == constants.strings.STATUS_CODE_SUCCESS:
                target_topic = constants.mqtt.CLUSTER_TOPIC + '/' + target_device['cluster'] if target_device['cluster'] is not None else constants.mqtt.GLOBAL_TOPIC

                mqtt_client.publish(target_topic, 'update|device|' + target_device['id'], qos=2)
    except MultipleInvalid:
        abort(400)

    return jsonify(status_response)


@app.route('/update/cluster/', methods=['POST'])
def ota_cluster():
    status_response = {}
    status_response['status'] = ''
    status_response['message'] = ''

    id_schema = Schema({Required('id'): constants.json_schema.ID_VALIDATOR})

    try:
        cluster_id = id_schema(request.json)['id']
        target_cluster = helpers.get_cluster(cluster_id)

        if target_cluster is None:
            status_response['status'] = constants.strings.STATUS_CODE_MISSING_CLUSTER
            status_response['message'] = 'No Cluster with that ID exists!'
        elif target_cluster['type'] is None:
            status_response['status'] = constants.strings.STATUS_CODE_UNINITIALIZED
            status_response['message'] = 'Cluster has not been initialized!'
        else:
            status_response = uftp_handlers.distribute_updated_code(
                target_cluster['id'], is_cluster=True)

            if status_response['status'] == constants.strings.STATUS_CODE_SUCCESS:

                mqtt_client.publish(constants.mqtt.CLUSTER_TOPIC + '/' +
                            target_cluster['id'], 'update|cluster|' + target_cluster['id'], qos=2)
    except MultipleInvalid:
        abort(400)

    return jsonify(status_response)


@app.route('/delete/device/', methods=['DELETE'])
def delete_device():
    status_response = {}
    status_response['status'] = ''
    status_response['message'] = ''

    id_schema = Schema({Required('id'): constants.json_schema.ID_VALIDATOR})

    try:
        device_id = id_schema(request.json)['id']
        target_device = helpers.get_device(device_id)

        if target_device is None:
            status_response['status'] = constants.strings.STATUS_CODE_MISSING_DEVICE
            status_response['message'] = 'No device with that ID exists!'
        else:
            if target_device['cluster'] is not None:
                # Decouple from cluster
                clusters = file_io.read_clusters()
                cluster_index = helpers.find_index(
                    clusters, target_device['cluster'])
                clusters['data'][cluster_index]['devices'].remove(
                    target_device)
                file_io.write_clusters(clusters)

            devices = file_io.read_devices()
            device_index = helpers.find_index(devices, target_device['id'])
            devices['data'].pop(device_index)
            file_io.write_devices(devices)

            status_response['status'] = constants.strings.STATUS_CODE_SUCCESS
            status_response['message'] = 'Device deleted successfully!'
    except OSError:
        status_response['status'] = constants.strings.STATUS_CODE_ERROR
        status_response['message'] = 'Server Side Error Occurred!'
    except MultipleInvalid:
        abort(400)

    return jsonify(status_response)


@app.route('/delete/cluster/', methods=['DELETE'])
def delete_cluster():
    status_response = {}
    status_response['status'] = ''
    status_response['message'] = ''

    id_schema = Schema(
        {Required('id'): constants.json_schema.ID_VALIDATOR})

    try:
        cluster_id = id_schema(request.json)['id']

        cluster = helpers.get_cluster(cluster_id)

        if cluster is None:
            status_response['status'] = constants.strings.STATUS_CODE_MISSING_CLUSTER
            status_response['message'] = 'No cluster with that ID exists!'
        else:
            clusters = file_io.read_clusters()
            cluster_index = helpers.find_index(clusters, cluster['id'])
            clusters['data'].pop(cluster_index)
            file_io.write_clusters(clusters)

            # Recursively delete the devices
            if len(cluster['devices']) > 0:
                devices = file_io.read_devices()
                device_indices = [idx for idx, device in enumerate(
                    devices['data']) if device['id'] in cluster['devices']]

                for device_index in device_indices:
                    del devices['data'][device_index]

                file_io.write_devices(devices)

            status_response['status'] = constants.strings.STATUS_CODE_SUCCESS
            status_response['message'] = 'Cluster deleted (recusively) successfully!'
    except OSError:
        status_response['status'] = constants.strings.STATUS_CODE_ERROR
        status_response['message'] = 'Server Side Error Occurred!'
    except MultipleInvalid:
        abort(400)

    return jsonify(status_response)


@app.route('/register/device/', methods=['PATCH'])
def register_device_to_cluster():
    json_validator = Schema({
        Required('device_id'): constants.json_schema.ID_VALIDATOR,
        Required('cluster_id'): constants.json_schema.ID_VALIDATOR
    })

    status_response = {}
    status_response['status'] = ''
    status_response['message'] = ''

    try:
        data = json_validator(request.json)

        device = helpers.get_device(data['device_id'])
        cluster = helpers.get_cluster(data['cluster_id'])

        device_exists = device is not None
        cluster_exists = cluster is not None
        is_free_device = False if device_exists is not True else device['cluster'] is None

        if device_exists is not True:
            status_response['status'] = constants.strings.STATUS_CODE_MISSING_DEVICE
            status_response['message'] = 'No Device with that ID exists!'
        elif cluster_exists is not True:
            status_response['status'] = constants.strings.STATUS_CODE_MISSING_CLUSTER
            status_response['message'] = 'No Cluster with that ID exists!'
        elif is_free_device is not True:
            status_response['status'] = constants.strings.STATUS_CODE_MEMBERSHIP_EXISTS
            status_response['message'] = 'Device already a member of a cluster!'
        else:
            clusters = file_io.read_clusters()
            cluster_index = helpers.find_index(clusters, cluster['id'])
            clusters['data'][cluster_index]['devices'].append(device['id'])
            file_io.write_clusters(clusters)

            devices = file_io.read_devices()
            device_index = helpers.find_index(devices, device['id'])
            devices['data'][device_index]['cluster'] = cluster['id']
            file_io.write_devices(devices)

            status_response['status'] = constants.strings.STATUS_CODE_SUCCESS
            status_response['message'] = 'Device registered to cluster successfully!'
    except MultipleInvalid:
        abort(400)
    
    return jsonify(status_response)
