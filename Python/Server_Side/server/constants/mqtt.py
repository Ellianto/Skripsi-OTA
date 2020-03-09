GLOBAL_TOPIC  = 'ota/control'
CLUSTER_TOPIC = 'ota/cluster'

# use the free broker from HIVEMQ
MQTT_CLIENT_ID   = 'main_server'
MQTT_BROKER_URL  = 'broker.hivemq.com'
MQTT_BROKER_PORT = 1883
MQTT_KEEPALIVE   = 5
MQTT_TLS_ENABLED = False

UPDATE_CODE = 'update'
DEVICE_CODE = 'device'
INIT_CODE   = 'init'

CMD_SEPARATOR = '|'

MQTT_MESSAGES = [
    'Successfully connected to MQTT Broker!'
    'Incorrect Protocol Version!',
    'Invalid Client ID!',
    'MQTT Server/Broker is unavailable!',
    'Bad Username/Password!',
    'Authorization Failed!'
]

UNHANDLED_MQTT_ERRORS = 'Invalid Return Code!'
