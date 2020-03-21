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

#this list contains array of esp32 clients,
# and each client contains mDNS name and the path to .bin file
#I only have 1 ESP so I duplicate mDNS entry for testing


ip_of_sender = '192.168.137.1'
target_esp_port = '8266'

def single_target():
    esps = [
        #IP Addr of ESP   #absolute path to ".bin" file
        # ['192.168.137.204', str(CURR_DIR / 'run.ino.nodemcu.bin')],
        ['192.168.137.111', str(CURR_DIR / 'run.ino.nodemcu.bin')]
    ]
    start = timeit.default_timer()
    # Sleep between 3 - 5 seconds to emulate transfer to gateway
    time.sleep(random.randrange(300,500)/100)
    
    for esp in esps:
        # cmd = 'python espota.py -i '+esp[0]+' -I '+ip_of_sender + ' -p '+target_esp_port + \
        #     ' -P '+source_host_port+' -f '+esp[1]
        cmd = ['python', str(CURR_DIR / 'espota.py'),
                '-i', esp[0],
                '-I', ip_of_sender,
                '-p', target_esp_port,
                '-f', esp[1]
        ]

        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = p.communicate()
        print(stdout)

    print('Update done in ' + str(timeit.default_timer() - start) + ' seconds')


def multi_gw_target():
    esps = [
        #IP Addr of ESP   #absolute path to ".bin" file
        ['192.168.137.204', str(CURR_DIR / 'run.ino.nodemcu.bin')],
        ['192.168.137.111', str(CURR_DIR / 'run.ino.nodemcu.bin')]
    ]

    start = timeit.default_timer()
    
    for esp in esps:
        # Sleep between 3 - 5 seconds to emulate transfer to n gateway
        time.sleep(random.randrange(300,500)/100)
        # cmd = 'python espota.py -i '+esp[0]+' -I '+ip_of_sender + ' -p '+target_esp_port + \
        #     ' -P '+source_host_port+' -f '+esp[1]
        cmd = ['python', str(CURR_DIR / 'espota.py'),
                '-i', esp[0],
                '-I', ip_of_sender,
                '-p', target_esp_port,
                '-f', esp[1]
        ]

        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = p.communicate()
        print(stdout)

    print('Update done in ' + str(timeit.default_timer() - start) + ' seconds')


    time.sleep(random.randrange(300,500)/100)


def clustered_target():
    esps = [
        #IP Addr of ESP   #absolute path to ".bin" file
        ['192.168.137.147', str(CURR_DIR / 'run.ino.nodemcu.bin')],
        ['192.168.137.252', str(CURR_DIR / 'run.ino.nodemcu.bin')],
        ['192.168.137.204', str(CURR_DIR / 'run.ino.nodemcu.bin')],
        ['192.168.137.111', str(CURR_DIR / 'run.ino.nodemcu.bin')]
    ]
    start = timeit.default_timer()
    # Sleep between 3 - 5 seconds to emulate transfer to gateway
    time.sleep(random.randrange(300,500)/100)
    
    for esp in esps:
        # cmd = 'python espota.py -i '+esp[0]+' -I '+ip_of_sender + ' -p '+target_esp_port + \
        #     ' -P '+source_host_port+' -f '+esp[1]
        cmd = ['python', str(CURR_DIR / 'espota.py'),
                '-i', esp[0],
                '-I', ip_of_sender,
                '-p', target_esp_port,
                '-f', esp[1]
        ]

        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = p.communicate()
        print(stdout)

    print('Update done in ' + str(timeit.default_timer() - start) + ' seconds')


if __name__ == '__main__':
    # single_target()
    # multi_gw_target()
    clustered_target()
    sys.exit(0)
