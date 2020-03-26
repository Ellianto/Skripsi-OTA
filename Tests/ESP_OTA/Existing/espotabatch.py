"""
    Credits to Tech It Yourself at
    http://www.iotsharing.com/2017/05/how-to-update-firmware-ota-for-batch-esp32.html
"""

import subprocess
import time
import sys
import random
from pathlib import Path
import timeit

CURR_DIR = Path(__file__).parent.absolute()

ip_of_sender = '192.168.66.1'
target_esp_port = '8266'
binfile = str(CURR_DIR / 'run.ino.nodemcu.bin')
esp_ota_script = str(CURR_DIR / 'espota.py')

esps = [
    #IP Addr of ESP   #absolute path to ".bin" file
    ['192.168.66.25', binfile], #x01
    ['192.168.66.86', binfile], #x02
    ['192.168.66.48', binfile], #x03
    ['192.168.66.56', binfile]  #x04
]

def run_update():
    start = timeit.default_timer()
    for esp in esps:
        cmd = ['python3', esp_ota_script,
                '-i', esp[0],
                '-I', ip_of_sender,
                '-p', target_esp_port,
                '-f', esp[1]
        ]

        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = p.communicate()
        print(stdout)
        print(stderr)

    print('Update done in ' + str(timeit.default_timer() - start) + ' seconds')

if __name__ == '__main__':
    run_update()
    sys.exit(0)