
# Request Status Responses
STATUS_CODE_SUCCESS = 'success'
STATUS_CODE_PARTIAL_FAILURE = 'partial_failure'
STATUS_CODE_FAILED = 'failed'
STATUS_CODE_ERROR = 'error'

STATUS_CODE_DEVICE_EXISTS = 'device_exists'
STATUS_CODE_CLUSTER_EXISTS = 'cluster_exists'
STATUS_CODE_MEMBERSHIP_EXISTS = 'membership_exists'

STATUS_CODE_MISSING_DATA    = 'missing_data'
STATUS_CODE_MISSING_DEVICE  = 'missing_device'
STATUS_CODE_MISSING_CLUSTER = 'missing_cluster'
STATUS_CODE_MISSING_GATEWAY = 'missing_gateway'

STATUS_CODE_UNINITIALIZED = 'uninitialized'
STATUS_CODE_CLUSTER_MISMATCH = 'cluster_mismatch'
STATUS_CODE_UFTP_INSTANCE_RUNNING = 'instance_running'


from . import mqtt as mqtt_constants

# MQTT Messages
ERROR_SUFFIX = 'when connecting to ' + mqtt_constants.MQTT_BROKER_URL

MQTT_MESSAGES = [
    'Successfully connected to ' + mqtt_constants.MQTT_BROKER_URL,
    'Incorrect Protocol Version detected ' + ERROR_SUFFIX,
    'Invalid Client ID detected ' + ERROR_SUFFIX,
    'MQTT Server/Broker is unavailable' + ERROR_SUFFIX,
    'Bad Username/Password detected ' + ERROR_SUFFIX,
    'Failed to authorize' + ERROR_SUFFIX,
]

UNHANDLED_MQTT_ERRORS = 'Invalid Return Code '
