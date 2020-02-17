from voluptuous import (All, Any, Coerce, Length, Match, Maybe,
                        MultipleInvalid, Required, Schema)

# JSON Validation Schemas
ID_VALIDATOR = All(Coerce(str, msg='Invalid variable type, expected str'), Length(
    min=8, max=30, msg='Invalid Length, expected 8-30 char'), Match(r'^[A-Za-z_][A-Za-z0-9_]{7,29}$'))

DEVICE_SCHEMA = Schema({
    Required('id'): ID_VALIDATOR,
    Required('type', default=None): Coerce(str),
    Required('cluster', default=None): Any(Maybe(str), ID_VALIDATOR),
    Required('gateway'): All(Coerce(str), Match(r'^0x[0-9A-F]{8}$'))
})

CLUSTER_SCHEMA = Schema({
    Required('id'): ID_VALIDATOR,
    Required('type', default=None): Maybe(str, msg='Invalid "type" variable, expected str or None'),
    Required('devices', default=list): list,
    Required('gateways', default=list): list,
})

