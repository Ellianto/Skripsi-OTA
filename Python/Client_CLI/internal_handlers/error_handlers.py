from requests.exceptions import HTTPError, ConnectionError
from voluptuous.error import MultipleInvalid

from constants import messages
from internal_handlers.helpers import getch

# Error Handlings

def handle_errors(incoming_exception, handled_exceptions):
    handled_error = next((message for exception_type, message in handled_exceptions if isinstance(incoming_exception, exception_type)), None)

    if handled_error is None:
        raise

    print(handled_error)
    getch()


def handle_misinput(exception):
    handle_errors(exception, [
        (ValueError, messages.CHOICE_TYPE_ERROR_MESSAGE),
        (IndexError, messages.CHOICE_OUT_OF_RANGE_MESSAGE),
        (EOFError, messages.USER_BREAK_MESSAGE)
    ])


def handle_request_exceptions(exception):
    handle_errors(exception, [
        (HTTPError, messages.HTTP_ERROR_MESSAGE),
        (ValueError, messages.INVALID_JSON_MESSAGE),
        (TimeoutError, messages.TIMEOUT_ERROR_MESSAGE),
        (MultipleInvalid, messages.BAD_RESPONSE_MESSAGE),
        (ConnectionError, messages.CONNECTION_ERROR_MESSAGE),
        (ConnectionRefusedError, messages.CONNECTION_REFUSED_MESSAGE),
    ])
# End of Error Handlings
