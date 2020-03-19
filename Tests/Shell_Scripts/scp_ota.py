import timeit
from pathlib import Path
from subprocess import PIPE, Popen

CURR_DIR = Path(__file__).parent.absolute()

distributor = str(CURR_DIR / 'main_distribute.sh')
file_src = str(CURR_DIR / 'run.py')

gateway_addr = '192.168.1.12'

end_device_addrs = [
    '192.168.66.4',
    '192.168.66.150',
    '192.168.66.174'
]

def classic_ota():
    for end_device_addr in end_device_addrs:
        ota_proc = Popen(['/bin/bash', distributor, file_src, gateway_addr, end_device_addr], stdout=PIPE, stderr=PIPE)
        output, errors = ota_proc.communicate()
        print('Standard Output : ')
        print('-' * 30)
        print('Standard Error :')
        print('#' * 30)

if __name__ == "__main__":
    start = timeit.default_timer()
    classic_ota()
    print('Finished in :' + str(timeit.default_timer() - start) + ' seconds')
