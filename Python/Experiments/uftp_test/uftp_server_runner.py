from pathlib import Path
from subprocess import PIPE
import psutil
import json

# Can be arbritratily defined
process_timeout = 30  # in seconds

# UFTP Manual defaults to IPv4 address (converted to Hex) or last 4 bytes of IPv6 address
server_uid = '0xABCDABCD'
transfer_rate = '1024'  # UFTP Manual defaults to 1000, we try using 1024 Kbps

# TODO: Might have to add randomizer to this (with a certain range)
# To enable multiple server process running at once
port_number = '1044'  # Default from the UFTP manual
pub_multicast_addr = '230.4.4.1'  # Default from the UFTP manual
# Default from the UFTP manual, the 'x' will be randomized
prv_multicast_addr = '230.5.5.x'

# The directory where the status files, log files, information files and files to be sent will be placed
curr_dir = Path(__file__).parent.absolute()

base_dir = curr_dir / 'data'
uftp_dir = curr_dir / 'uftp'

status_file = uftp_dir / 'status.txt'
log_file = uftp_dir / 'uftp_server_logfile.txt'

path_to_uftp_server_exe = uftp_dir / 'uftp.exe'

max_log_size = '2'  # in MB, specifies limit size before a log file is backed up
max_log_count = '5'  # Default UFTP Value, keeps max 5 iterations of log backups

# Still need to append client list and file list/target direactory
uftp_server_commands = [str(path_to_uftp_server_exe),
                        '-l',  # Unravel Symbolic Links
                        '-z',  # Run the Server in Sync Mode, so clients will only receive new/updated files
                        '-t', '3',  # TTL value for Multicast Packets, by default is 1 so we turn it up a little
                        '-U', server_uid,  # Server UID for identification purposes. Clients can select which server to receive from based on Server's UID
                        # Transfer rate in Kbps, if undefined will be set to 1000 by the UFTP Server. We set to 1024 Kbps = 128KB/s
                        '-R', transfer_rate,
                        '-E', str(base_dir),  # Base directory for the sent files, relevant only for subdirectory management in the client side
                        '-S', str(status_file),   # Output for persable STATUS File, can be used to confirm the file transfer process' result. Only relevant in SYNC MODE
                        '-L', str(log_file),  # The log file output. If undefined, UFTP manual defaults to printing logs to stderr
                        '-g', max_log_size,
                        '-n', max_log_count,
                        '-p', port_number,  # The port number the server will be listening from
                        '-M', pub_multicast_addr,  # The Initial Public Multicast Address for the ANNOUNCE phase
                        '-P', prv_multicast_addr,  # The Private Multicast Address for FILE TRANSFER phase
                        '-H']  # List of comma separated target client IDs, enclosed in "" if more than one (0x prefix optional)

def uftp_server_runner(target_id, is_cluster=False, retries=2):
    try:
        status_response = {}
        status_response['status'] = ''

        try:
            proc_name = 'uftp.exe'
            uftp_server_check = next(
                proc for proc in psutil.process_iter() if proc.name() == proc_name)

            print('Another UFTP Server Instance is currently running!')
            print('UFTP Server Instance Information:')
            print(uftp_server_check.as_dict())

            status_response['status'] = 'instance_running'
            status_response['instance_info'] = uftp_server_check.as_dict()

        except StopIteration:
            status_response['session_info'] = []
            attempts = 0

            all_good = None

            while attempts <= retries:
                session_info = {}
                status_data = {}

                gateway_ids = []
                target_dir = ''

                # TODO: Fetch info from JSON file here
                if is_cluster is True:
                    gateway_ids = ['0x12341234', '0xABCDABCD', '0x00998877']
                    target_dir = base_dir / 'cluster' / str(target_id)
                elif is_cluster is False:
                    gateway_ids = [target_id]
                    target_dir = base_dir / 'devices' / str(target_id)

                if target_dir.exists() is False:
                    break

                session_info['gateways_list'] = gateway_ids
                session_info['target_dir'] = str(target_dir)

                host_list = ','.join(gateway_id for gateway_id in gateway_ids)
                print(host_list)

                if len(gateway_ids) > 1:
                    host_list = '"' + host_list + '"'

                with psutil.Popen(uftp_server_commands + [host_list, str(target_dir)]) as uftp_server:
                    print(uftp_server.cmdline())
                    return_code = uftp_server.wait(timeout=process_timeout)

                message = ''

                if return_code in [2, 3, 4, 5, 6, 9]:
                    message = 'An error occurred!'
                elif return_code in [7, 8]:
                    message = 'No Clients responded!'
                elif return_code in [1, 10]:
                    message = 'Session Complete!'

                    with status_file.open() as f:
                        lines = [line.rstrip().split(';') for line in f]

                    status_data = parse_lines(lines)

                    # Check for any failure in this session
                    all_good = len([val for val in status_data['FAILED'].values() if len(val) > 0]) == 0
                else:
                    message = 'Something wrong occured!'


                print(message)
                session_info['message'] = message
                session_info['return_code'] = return_code

                status_response['session_info'].append({**session_info, 'status_file' : status_data})

                if all_good is True:
                    break
                else:
                    attempts += 1

            if all_good is True:
                status_response['status'] = 'success' 
            elif all_good is False:
                status_response['status'] = 'failed'
            elif all_good is None:
                status_response['status'] = 'target_dir_not_found'

    except TimeoutExpired:
        # If UFTP Server runs longer than the defined timeout value
        print('UFTP Server Timed Out! Re-tune the parameters or try again')
        status_response['status'] = 'timeout'
    finally:
        # Deletes the status file so that the next session starts with a clean file
        if status_file.exists() is True:
            status_file.unlink()

        return status_response

"""
Before running, the file(s) to be sent must be prepared in a directory with this structure:
(base_dir)/(device or cluster)/(device or cluster ID)

For example, with the default base_dir (./data/) and target cluster ID of "example_cluster":
./data/cluster/example_cluster

The first parameter should be the device/cluster ID, but here it is directly the target gateway ID
"""

if __name__ == '__main__':
    print(uftp_server_runner('0x12341234'))