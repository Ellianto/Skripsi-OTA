from voluptuous import All, Any, Maybe, Coerce, Length, Range, Match, Required, Optional, Schema

# TODO: determine what other infos are needed server-side
SERVER_CONF_VALIDATOR = Schema({
    Optional('status'): Coerce(str),
    Optional('message') : Coerce(str),
    Required('gateway_uid'): All(Coerce(str), Match(r'^0x[0-9A-F]{8}$')),
    Required('mqtt_topic', default='ota/global'): Coerce(str),
    Required('mqtt_broker', default='broker.hivemq.com'): Coerce(str),
    Required('end_device_multicast_addr', default='230.6.6.1'): All(Coerce(str), Match(r'^(22[4-9]|230)(.([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])){3}$')),
    Required('max_log_size', default='2'):  All(Coerce(str), Match(r'^\d{1,2}$')),
    Required('max_log_count', default='5'): All(Coerce(str), Match(r'^\d{1,2}$')),
    Required('buffer_size', default=1024): All(Coerce(int), Range(min=64, max=1460))
})

END_DEVICE_CONF_VALIDATOR = Schema({
    Required('id'): All(Coerce(str, msg='Invalid variable type, expected str'), Length(
        min=8, max=30, msg='Invalid Length, expected 8-30 char'), Match(r'^[A-Za-z_][A-Za-z0-9_]{7,29}$')),
    Required('cluster'): Any(Maybe(str), All(Coerce(str, msg='Invalid variable type, expected str'), Length(
        min=8, max=30, msg='Invalid Length, expected 8-30 char'), Match(r'^[A-Za-z_][A-Za-z0-9_]{7,29}$'))),
    Required('type'): str
})
