from server import constants, mqtt_client
from server.internal_handlers import file_io

# MQTT Functions
@mqtt_client.on_connect()
def handle_connect(client, userdata, flags, rc):
    if rc in range(len(constants.mqtt.MQTT_MESSAGES)):
        print(constants.mqtt.MQTT_MESSAGES[rc])
    else:
        print(constants.mqtt.UNHANDLED_MQTT_ERRORS + '(' + str(rc) + ')')

    if rc == 0:
        mqtt_client.subscribe(constants.mqtt.GLOBAL_TOPIC, qos=2)
        mqtt_client.subscribe(constants.mqtt.CLUSTER_TOPIC, qos=2)


@mqtt_client.on_message()
def handle_message(client, userdata, msg):
    print("Message Received from topic " + str(
        msg.topic) + ' : ' + str(msg.payload.decode()))

    mqtt_message = msg.payload.decode().split(constants.mqtt.CMD_SEPARATOR)

    if mqtt_message[0] == constants.mqtt.INIT_CODE:
        # Check if UID already exists
        gateways = file_io.read_gateways()

        gateway_exists = next((
            gateway['id'] for gateway in gateways['data'] if gateway['id'] == str(mqtt_message[1])), None)

        if gateway_exists is None:
            gateways['data'].append({
                "id": str(mqtt_message[1]),
                "cluster": [],
                "device": []
            })

            file_io.write_gateways(gateways)

# End of MQTT Functions
