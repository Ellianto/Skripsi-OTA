from voluptuous import All, Any, Maybe, Coerce, Length, Range, Match, Required, Optional, Schema

SERVER_CONF_VALIDATOR = Schema({
    Required('status'): Coerce(str),
    Required('message') : Coerce(str),
    Optional('gateway_uid'): All(Coerce(str), Match(r'^0x[0-9A-F]{8}$')),
    Optional('mqtt_topic', default='ota/global'): Coerce(str),
    Optional('mqtt_broker', default='broker.hivemq.com'): Coerce(str),
    Optional('end_device_multicast_addr', default='230.6.6.1:7777'): All(Coerce(str), Match(r'^(22[4-9]|230)(\.([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])){3}:\d{3,4}$')),
    Optional('max_log_size', default='2'):  All(Coerce(str), Match(r'^\d{1,2}$')),
    Optional('max_log_count', default='5'): All(Coerce(str), Match(r'^\d{1,2}$')),
    Optional('buffer_size', default=1024): All(Coerce(int), Range(min=64, max=1460))
})

END_DEVICE_CONF_VALIDATOR = Schema({
    Required('code'): Coerce(str),
    Required('id'): All(Coerce(str, msg='Invalid variable type, expected str'), Length(
        min=8, max=30, msg='Invalid Length, expected 8-30 char'), Match(r'^[A-Za-z_][A-Za-z0-9_]{7,29}$')),
    Required('cluster'): Any(Maybe(str), All(Coerce(str, msg='Invalid variable type, expected str'), Length(
        min=8, max=30, msg='Invalid Length, expected 8-30 char'), Match(r'^[A-Za-z_][A-Za-z0-9_]{7,29}$'))),
    Required('type'): str
})

SERVER_RESPONSE_VALIDATOR = Schema({
    Required('status') : Coerce(str),
    Required('message') : Coerce(str)
})
