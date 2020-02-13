from requests.exceptions import HTTPError, ConnectionError
from voluptuous.error import MultipleInvalid

from constants import messages
from internal_handlers.helpers import getch

# Error Handlings
misinput_exceptions = [
    (ValueError, messages.CHOICE_TYPE_ERROR_MESSAGE),
    (IndexError, messages.CHOICE_OUT_OF_RANGE_MESSAGE)
]

def handle_misinput(exception):
    error_message = [msg for ex, msg in misinput_exceptions if isinstance(exception, ex)]

    if len(error_message) == 0:
        raise

    print(error_message[0])
    getch()

request_exceptions = [
    (HTTPError, messages.HTTP_ERROR_MESSAGE),
    (ValueError, messages.INVALID_JSON_MESSAGE),
    (TimeoutError, messages.TIMEOUT_ERROR_MESSAGE),
    (MultipleInvalid, messages.BAD_RESPONSE_MESSAGE),
    (ConnectionError, messages.CONNECTION_ERROR_MESSAGE),
    (ConnectionRefusedError, messages.CONNECTION_REFUSED_MESSAGE),
]

def handle_request_exceptions(exception):
    error_message = [msg for ex, msg in request_exceptions if isinstance(exception, ex)]

    if len(error_message) == 0:
        raise

    print(error_message[0])
    getch()
# End of Error Handlings
