from pathlib import Path
from platform import system as os_type

CURR_DIR = Path(__file__).parent.absolute()

CODE_DIR = CURR_DIR / 'code'
TEMP_DIR = CURR_DIR / 'temp'

SCRIPT_FILE = CURR_DIR / ('start.sh' if os_type() != 'Windows' else 'start.bat')
TEMP_DATA_FILE = CURR_DIR / 'temp.zip'
CONFIG_FILE = CURR_DIR / 'config.json'
