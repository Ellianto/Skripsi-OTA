import psutil
import shutil

import server.constants as constants
import server.internal_handlers.helpers as helper


"""
Before running, the file(s) to be sent must be prepared in a directory with this structure:
(BASE_DIR)/(device or cluster)/(device or cluster ID)

For example, with the default BASE_DIR (./data/) and target cluster ID of "example_cluster":
./data/cluster/example_cluster
"""

def compress_to_zip():
    pass

def check_uftp_server_instance():
    proc_name = 'uftp.exe'
    return next(
        (proc for proc in psutil.process_iter() if proc.name() == proc_name), None)


def initialize_params(target_id, is_cluster=False):
    init_obj = {}
    init_obj['status_code'] = ''
    init_obj['message'] = ''
    gateway_ids = []
    target_dir = None

    if is_cluster is False:
        target_device = helper.get_device(target_id)

        if target_device is None:
            init_obj['status_code'] = constants.strings.STATUS_CODE_MISSING_DEVICE
            init_obj['message'] = 'No Device with that ID exists!'
        else:
            gateway_ids = [] if target_device['gateway'] is None else [target_device['gateway']]
            target_dir = constants.paths.BASE_DIR / 'device' / target_device['id']
    else:
        target_cluster = helper.get_cluster(target_id)

        if target_cluster is None:
            init_obj['status_code'] = constants.strings.STATUS_CODE_MISSING_CLUSTER
            init_obj['message'] = 'No Cluster with that ID exists!'
        else:
            gateway_ids = target_cluster['gateways']
            target_dir = constants.paths.BASE_DIR / 'cluster' / target_cluster['id']

    if target_dir is not None:
        if target_dir.exists() is not True:
            init_obj['status_code'] = constants.strings.STATUS_CODE_MISSING_DATA
            init_obj['message'] = 'Target file not found!'
        elif len(gateway_ids) == 0:
            init_obj['status_code'] = constants.strings.STATUS_CODE_UNINITIALIZED
            init_obj['message'] = 'Target Device/Cluster has not been initialized yet!'
        else:
            init_obj['status_code'] = constants.strings.STATUS_CODE_SUCCESS
            init_obj['message'] = 'Parameter Initialization Successful!'

            shutil.make_archive(str(target_dir / target_id), 'zip', str(target_dir))
    
    init_obj['target_file'] = None if target_dir is None else str(target_dir / (target_id + '.zip'))
    init_obj['gateway_ids'] = gateway_ids

    return init_obj


def parse_status_file():
    connect_arr = []
    stats_arr = []
    results = {}
    failed_gateways = {
        'conn_failed': set(),
        'rejected': set(),
        'lost': set()
    }

    with constants.paths.STATUS_FILE_PATH.open() as f:
        lines = [line.rstrip().split(';') for line in f]

    for line in lines:
        if line[0] == 'CONNECT':
            if line[1] == 'success':
                connect_arr.append(line)
            elif line[1] == 'failed':
                failed_gateways['conn_failed'].add(line[2])

        elif line[0] == 'RESULT':
            if line[4] in ['copy', 'overwrite', 'skipped']:
                if line[1] not in results:
                    results[line[1]] = []
                results[line[1]].append(line)
            elif line[4] in ['rejected', 'lost']:
                failed_gateways[line[4]].add(line[1])

        elif line[0] == 'STATS':
            if line[1] in failed_gateways['conn_failed']:
                pass
            else:
                stats_arr.append(line)

    return {
        'CONNECT': connect_arr,
        'RESULT': results,
        'STATUS': stats_arr,
        'FAILED': failed_gateways,
    }


def run_uftp_server(gateway_ids, target_file, retries=2):
    session_list = []
    success = None
    hostlist = ','.join(gateway_id for gateway_id in gateway_ids)

    if len(gateway_ids) > 0:
        hostlist = '"' + hostlist + '"'

    for attempts in range(retries):
        message = ''
        status_data = {}

        try:
            with psutil.Popen(constants.uftp.UFTP_SERVER_CMD + [hostlist, target_file]) as uftp_server:
                return_code = uftp_server.wait(timeout=constants.uftp.PROCESS_TIMEOUT)

            if return_code in [1, 2, 3, 4, 5, 6, 9]:
                message = 'An error occurred!'
            elif return_code in [7, 8]:
                message = 'No Clients responded!'
            elif return_code in [0, 10]:
                message = 'Session Complete!'
                status_data = parse_status_file()
                success = len([val for val in status_data['FAILED'].values() if len(val) > 0]) == 0
                if success is True:
                    break
            else:
                message = 'Something wrong occured!'
        except TimeoutError:
            message = 'UFTP Server execution timed out!'
            print(message)
        finally:
            session_list.append({'info' : message, **status_data})

    return success, session_list


def distribute_updated_code(target_id, is_cluster=False, retries=2):
    status_response = {}
    status_response['status'] = ''
    status_response['message'] = ''

    try:
        if check_uftp_server_instance() is not None:
            status_response['status'] = constants.strings.STATUS_CODE_UFTP_INSTANCE_RUNNING
            status_response['message'] = 'Another UFTP Server Instance is currently running!'
        else:
            params = initialize_params(target_id, is_cluster=is_cluster)

            if params['status_code'] == constants.strings.STATUS_CODE_SUCCESS:
                session_info = {}
                session_info['gateway_list'] = params['gateway_ids']
                session_info['target_file'] = params['target_file']

                success, session_report = run_uftp_server(params['gateway_ids'], params['target_file'], retries=retries)

                session_info['session_report'] = session_report
                status_response['session_info'] = session_info
                
                if success is True:
                    status_response['status'] = constants.strings.STATUS_CODE_SUCCESS
                    status_response['message'] = 'Code transferred to Gateway successfully!'
                elif success is False:
                    status_response['status'] = constants.strings.STATUS_CODE_PARTIAL_FAILURE
                    status_response['message'] = 'Some gateways failed receiving data!'
                elif success is None:
                    status_response['status'] = constants.strings.STATUS_CODE_FAILED
                    status_response['message'] = 'Code transfer failed!'
            else:
                status_response['status'] = params['status_code']
                status_response['message'] = params['message']
    except:
        status_response['status'] = constants.strings.STATUS_CODE_ERROR
        status_response['message'] = 'An error occurred!'
        raise
    finally:
        if constants.path.STATUS_FILE_PATH.exists() is True:
            constants.paths.STATUS_FILE_PATH.unlink()

    return status_response
