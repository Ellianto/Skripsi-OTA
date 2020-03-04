from pathlib import Path

CURR_DIR = Path(__file__).parent.absolute()

#  UFTP Dirs
BACKUP_DIR = CURR_DIR / 'backup_data'
DEST_DIR = CURR_DIR / 'main_data'

UFTP_DIR = CURR_DIR / 'uftp'

STATUS_FILE_PATH = UFTP_DIR / 'status.txt'
LOG_FILE_PATH = UFTP_DIR / 'uftp_client_logfile.txt'
UFTP_CLIENT_EXE_PATH = UFTP_DIR / 'uftpd.exe'

# Config file
CONF_FILE_PATH = CURR_DIR / 'config.json'
DEVICES_FILE_PATH = CURR_DIR / 'devices.json'
CLUSTERS_FILE_PATH = CURR_DIR / 'clusters.json'
