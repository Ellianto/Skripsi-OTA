import netifaces as ni

# Server Base URL Should be used in conjunction with modifications to hosts file
MTU_SIZE = 1460
SERVER_PORT = 9999

SERVER_BASE_URL = 'http://skripsi_server:' + str(SERVER_PORT) + '/'
INIT_GATEWAY_ENDPOINT =  SERVER_BASE_URL + 'init/gateway/'
INIT_DEVICE_ENDPOINT = SERVER_BASE_URL + 'init/device/'

AP_ADDRESS = ni.ifaddresses('ap0')[ni.AF_INET][0]['addr']

CMD_MSG_SEPARATOR = '|'