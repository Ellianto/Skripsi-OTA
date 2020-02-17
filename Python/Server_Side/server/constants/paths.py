from server import ROOT_DIR

BASE_DIR = ROOT_DIR / 'data'

DEVICES_FILE_PATH = BASE_DIR / 'devices.json'
CLUSTERS_FILE_PATH = BASE_DIR / 'clusters.json'
GATEWAYS_FILE_PATH = BASE_DIR / 'gateways.json'

UFTP_DIR = ROOT_DIR / 'uftp'

STATUS_FILE_PATH = UFTP_DIR / 'status.txt'
LOG_FILE_PATH = UFTP_DIR / 'uftp_server_logfile.txt'
UFTP_SERVER_EXE_PATH = UFTP_DIR / 'uftp.exe'

FILE_LIST = [DEVICES_FILE_PATH, CLUSTERS_FILE_PATH, GATEWAYS_FILE_PATH]
DIR_LIST = [BASE_DIR / 'clusters', BASE_DIR / 'devices']
