import subprocess
import psutil
from pathlib import Path

# An absolute path is required (for the Destination Directory)
# If the directories did not exist, it will be created
curr_dir = Path(__file__).parent.absolute()

backup_dir = curr_dir / 'backup_data'
destination_dir = curr_dir / 'main_data'

statusfile_path = curr_dir / 'status.txt'
logfile_path = curr_dir / 'uftp_client_logfile.txt'
path_to_uftp_client_exe = curr_dir / 'uftp' / 'uftpd.exe'

max_log_size = '2' # in MB, specifies limit size before a log file is backed up
max_log_count = '5' # Default UFTP Value, keeps max 5 iterations of log backups

client_uid = '0x12341234'

uftp_client_cmd = [str(path_to_uftp_client_exe), 
                    '-d',
                    '-t', 
                    '-D', str(destination_dir), 
                    '-A', str(backup_dir), 
                    '-U', str(client_uid), 
                    '-L', str(logfile_path),
                    '-g', max_log_size,
                    '-n', max_log_count,
                    '-F', str(statusfile_path)]

def directory_check():
    dirs = [destination_dir, backup_dir]

    for dir in dirs:
        if dir.exists() is not True:
            print('Directory {} not detected, creating directory...'.format(str(dir)))
            dir.mkdir(parents=True)
        else:
            print('Directory {} checked, exists'.format(str(dir)))


try:
    directory_check()
    proc_name = 'uftpd.exe'
    uftpd_process = next(p for p in psutil.process_iter() if p.name() == proc_name)
    
except StopIteration:
    # via psutil Module
    uftp_client = psutil.Popen(uftp_client_cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)

    # is_running() will also return True if it is a zombie process
    if uftp_client.is_running() is True:        
        print('Started UFTP Client Daemon with PID : {}'.format(uftp_client.pid))
    else:
        print('Something wrong happened while starting UFTP Client Daemon!')
        print('Status : {}'.format(uftp_client.status()))

    # via subprocess Module
    # uftp_client = subprocess.Popen(uftp_client_cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    # return_code = uftp_client.poll()

    # if return_code is None or return_code == 0:
    #     print('Started UFTP Client Daemon with PID : {}'.format(uftp_client.pid))
    # else:
    #     print('Something wrong happened while starting UFTP Client Daemon!')
    #     print('Return Code : {}'.format(return_code))
except:
    print('Something Happened!')
    raise
else:
    print('UFTP Client Daemon is already running!')
