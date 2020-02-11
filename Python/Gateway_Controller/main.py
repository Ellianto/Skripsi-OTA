import psutil

from pathlib import Path
from subprocess import PIPE

curr_dir = Path(__file__).parent.absolute()

backup_dir = curr_dir / 'backup_data'
destination_dir = curr_dir / 'main_data'

uftp_dir = curr_dir / 'uftp'

status_file_path = uftp_dir / 'status.txt'
log_file_path = uftp_dir / 'uftp_client_logfile.txt'
path_to_uftp_client_exe = uftp_dir / 'uftpd.exe'

# TODO: Set these in config files
max_log_size = '2'  # in MB, specifies limit size before a log file is backed up
max_log_count = '5'  # Default UFTP Value, keeps max 5 iterations of log backups

client_uid = '0x12341234'

uftp_client_cmd = [str(path_to_uftp_client_exe),
                    '-d',
                    '-t',
                    '-D', str(destination_dir),
                    '-A', str(backup_dir),
                    '-U', str(client_uid),
                    '-L', str(log_file_path),
                    '-g', max_log_size,
                    '-n', max_log_count,
                    '-F', str(status_file_path)]

# Initializer Functions
def init_dirs():
    dirs = [destination_dir, backup_dir]

    for dir in dirs:
        if dir.exists() is not True:
            print('Directory {} not detected, creating directory...'.format(str(dir)))
            dir.mkdir(parents=True)
        else:
            print('Directory {} checked, exists'.format(str(dir)))


def init_files():
    pass

def init_uftp():
    return_code = None

    try:
        proc_name = 'uftpd.exe'
        uftpd_instance = next(proc for proc in psutil.process_iter() if proc.name() == proc_name)
    except StopIteration:
        with psutil.Popen(uftp_client_cmd) as uftp_client_daemon:
            if uftp_client_daemon.is_running() is True:
                print('Started UFTP Client Daemon with PID : {}'.format(
                    uftp_client_daemon.pid))
                return_code = 0
            else:
                print('Something wrong happened while starting UFTP Client Daemon!')
                print('Status : {}'.format(uftp_client_daemon.status()))
                return_code = 2
    except:
        print('Something Happened!')
        raise
    else:
        print('UFTP Client Daemon already running!')
        return_code = 1

    return return_code:

def init_lwm2m():
    pass

def init_mqtt():
    pass

# End of initializers

# LWM2M Functions
def lwm2m_update():
    pass

# End of LWM2M Functions

# MQTT Functions

# End of MQTT Functions

if __name__ == '__main__':
    init_dirs()
    init_files()
    init_uftp()
    init_lwm2m()
    init_mqtt()
    
