from pathlib import Path
import platform

# Double parent so that it stays in the correct root directory
CURR_DIR = Path(__file__).parent.parent.absolute()

#  UFTP Dirs
BACKUP_DIR = CURR_DIR / 'backup_data'
DEST_DIR = CURR_DIR / 'main_data'

UFTP_DIR = CURR_DIR / 'uftp'

STATUS_FILE_PATH = UFTP_DIR / 'status.txt'
LOG_FILE_PATH = UFTP_DIR / 'uftp_client_logfile.txt'

UFTP_CLIENT_EXE_PATH = UFTP_DIR / ('uftpd' + ('.exe' if platform.system() == 'Windows' else ''))

# Config file
CONF_FILE_PATH = CURR_DIR / 'config.json'
DEVICES_FILE_PATH = CURR_DIR / 'devices.json'
CLUSTERS_FILE_PATH = CURR_DIR / 'clusters.json'

DIR_LIST = [DEST_DIR, BACKUP_DIR]
JSON_FILE_LIST = [DEVICES_FILE_PATH, CLUSTERS_FILE_PATH]
FILE_EXTENSIONS = {
    'ESP' : '.ino.nodemcu.bin',
    'RPi' : '.zip'
}