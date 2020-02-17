from server import constants, mqtt_client

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

# End of MQTT Functions
