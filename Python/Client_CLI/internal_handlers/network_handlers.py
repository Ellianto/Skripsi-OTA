import requests

from voluptuous import Required, Coerce, MultipleInvalid, Schema, ALLOW_EXTRA

from internal_handlers.error_handlers import handle_request_exceptions
from internal_handlers.helpers import getch
from constants import request_status

# Network Requests
def fetch_from_server(target_endpoint):
    request_data = None
    fetch_validator = Schema({Required('data') : list})

    try:
        response = requests.get(target_endpoint)

        if response.raise_for_status() is not None:
            raise requests.exceptions.HTTPError

        request_data = fetch_validator(response.json())
    except Exception as err:
        handle_request_exceptions(err)

    return request_data


def send_to_server(target_endpoint, data, method='POST'):
    request_ok = False
    status_validator = Schema({
        Required('status') : Coerce(str),
        Required('message') : Coerce(str),
    }, extra=ALLOW_EXTRA)

    try:
        if method == 'POST':
            response = requests.post(target_endpoint, json=data)
        elif method == 'PUT':
            response = requests.put(target_endpoint, json=data)
        elif method == 'PATCH':
            response = requests.patch(target_endpoint, json=data)

        if response.raise_for_status() is not None:
            raise requests.exceptions.HTTPError

        status_response = status_validator(response.json())
        print(status_response['message'])
        getch()

        request_ok = status_response['status'] == request_status.SUCCESS

    except Exception as err:
        handle_request_exceptions(err)

    return request_ok
# End of Network Requests
