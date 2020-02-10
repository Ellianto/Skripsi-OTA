from pathlib import Path
from subprocess import PIPE
import os
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

status_file = base_dir / 'status.txt'
log_file = base_dir / 'uftp_server_logfile.txt'

path_to_uftp_server_exe = curr_dir / 'uftp' / 'uftp.exe'

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
                        '-L', str(log_file)  # The log file output. If undefined, UFTP manual defaults to printing logs to stderr
                        '-g', max_log_size,
                        '-n', max_log_count,
                        '-p', port_number,  # The port number the server will be listening from
                        '-M', pub_multicast_addr,  # The Initial Public Multicast Address for the ANNOUNCE phase
                        '-P', prv_multicast_addr,  # The Private Multicast Address for FILE TRANSFER phase
                        '-H']  # List of comma separated target client IDs, enclosed in "" (0x prefix optional)

def check_failed_gateway_connect(connect_ids, gateway_ids):
    failed_gateways = [conn[2] for conn in connect_ids if conn[1] = 'failed']
    any_failed = len(failed_gateways) > 0

    if any_failed:
        print('Some gateways failed to connect to UFTP Session!')
        print('Failed gateways : ')

        for failed_gateway in failed_gateways:
            print('-> ' + failed_gateway)

    return any_failed


def parse_lines(lines):
    connect_arr = []
    results = {}
    stats_arr = []
    h_stats_arr = []
    failed_gateways = {
        'conn_failed': [],
        'rejected': [],
        'lost': []
    }

    for line in lines:
        if line[0] == 'CONNECT':
            if line[2] == 'success':
                connect_arr.append(line)
            elif line[2] == 'failed':
                failed_gateways['conn_failed'].append(line[2])
        elif line[0] == 'RESULT':
            if line[4] in ['copy', 'overwrite', 'skipped']:
                if line[1] not in results:
                    results[line[1]] = []
                result[line[1]].append(line)
            elif line[4] in ['rejected', 'lost'] and line[1] not in failed_gateways[line[4]]:
                failed_gateways[line[4]].append(line[1])
        elif line[0] == 'STATS':
            if line[1] in failed_gateways['conn_failed']:
                pass
            else:
                stats_arr.append(line)
        elif line[0] == 'HSTATS':
            h_stats_arr.append(line)

    return {
        'CONNECT' : connect_arr,
        'RESULT'  : results,
        'STATUS'  : stats_arr,
        'FAILED'  : failed_gateways,
    }


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

                if is_cluster is True:
                    # TODO: Fetch info from JSON file here
                    gateway_ids = ['0x12341234', '0xABCDABCD', '0x00998877']
                    target_dir = base_dir / 'cluster' / str(target_id)
                elif is_cluster is False:
                    gateway_ids = [target_id]
                    target_dir = base_dir / 'device' / str(target_id)

                session_info['gateways_list'] = gateway_ids
                session_info['target_dir'] = str(target_dir)

                host_list = '"' + ','.join(gateway_id for gateway_id in gateway_ids) + '"'

                with psutil.Popen(uftp_server_commands + [host_list, str(target_dir)]) as uftp_server:
                    return_code = uftp_server.wait(timeout=process_timeout)

                message = ''

                if return_code is None:
                    message = 'Something wrong occured!'
                elif return_code in [2, 3, 4, 5, 6, 9]:
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

                    if all_good is True:
                        break
                    else:
                        attempts += 1


                print(message)
                session_info['message'] = message
                session_info['return_code'] = return_code

                status_response['session_info'].append({**session_info, 'status_file' : status_data})

            status_response['status'] = 'success' if all_good is True else 'failed'

    except TimeoutExpired:
        # If UFTP Server runs longer than the defined timeout value
        print('UFTP Server Timed Out! Re-tune the parameters or try again')
        status_response['status'] = 'timeout'
    finally:
        # Deletes the status file so that the next session starts with a clean file
        status_file.unlink(missing_ok=True)
        return json.dumps(status_response)

# Play with the parameters here
print(uftp_server_runner())
