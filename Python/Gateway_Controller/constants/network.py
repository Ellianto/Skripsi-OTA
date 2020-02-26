import netifaces as ni

# Server Base URL Should be used in conjunction with modifications to hosts file
# SERVER_BASE_URL = http://skripsi_server/'
SERVER_BASE_URL = 'http://skripsi_server/'
INIT_GATEWAY_ENDPOINT =  SERVER_BASE_URL + 'init/gateway/'
INIT_DEVICE_ENDPOINT = SERVER_BASE_URL + 'init/device/'

# TODO: Change eth0 to virtual AP interface on Raspberry Pi Configuration
AP_ADDRESS = ni.ifaddresses('eth0')[ni.AF_INET][0]['addr']

CMD_MSG_SEPARATOR = '|'