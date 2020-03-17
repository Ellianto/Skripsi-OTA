from pathlib import Path
from platform import system as os_type

CURR_DIR = Path(__file__).parent.parent.absolute()

CODE_DIR = CURR_DIR / 'code'
TEMP_DIR = CURR_DIR / 'temp'

SCRIPT_FILE = CODE_DIR / 'run.py'
TEMP_DATA_FILE = CURR_DIR / 'temp.zip'
CONFIG_FILE = CURR_DIR / 'config.json'
