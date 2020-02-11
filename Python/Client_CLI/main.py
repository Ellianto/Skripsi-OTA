import os
import json
import platform

import requests

# Strings for messages & prompts
input_prompt = 'Enter your choice here : '
error_prompt = 'Press any key to continue... '
error_message = 'Please input a proper choice! '

input_id_prompt = 'Input the new Device ID (valid Python identifier, 8-30 chars), type 0 to return : '
invalid_identifier_message = 'Invalid Python Identifier! Valid Python Identifiers = alphanumeric, _ allowed, no spaces, doesn\'t start with number!'
incorrect_length_message = 'Inappropriate Length! Input 8-30 characters!'

http_error_message = 'Unsuccessful Request! HTTP Error Code '
connection_error_message = 'Network Problem! Check your (or the server\'s) network connection!'
timeout_error_message = 'Request Timed Out! Please try again!'
invalid_json_message = 'Invalid JSON Response From Server!'

base_url = 'http://localhost:5000/'

# Simplifying Functions

# TODO: Add logic for deleting device/cluster later

def getch():
    dump = input(error_prompt).split(' ')[0]


def handle_misinput():
    print(error_message)
    getch()


def clear_screen():
    curr_platform = platform.system()
    command = 'cls'  # For windows

    if curr_platform != 'Windows':
        # For Mac or Linux
        command = 'clear'

    os.system(command)


def send_to_endpoint(target_endpoint, data, method='POST'):
    try:
        if method == 'POST':
            response = requests.post(base_url + target_endpoint, json=data)
        elif method == 'PUT':
            response = requests.put(base_url + target_endpoint, json=data)
        elif method == 'PATCH':
            response = requests.patch(base_url + target_endpoint, json=data)

        if response.raise_for_status() is None:
            status_response = response.json()

            print(status_response)

            if status_response['status'] == 'success':
                print('Request Successful!')
            elif status_response['status'] == 'missing_device':
                print('Device does not exist!')
            elif status_response['status'] == 'missing_cluster':
                print('Cluster does not exist!')
            elif status_response['status'] == 'exists':
                print('Already Exists!')
            elif status_response['status'] == 'error':
                print(status_response['message'])
            else:
                print('Request Failed to execute!')
        else:
            raise requests.HTTPError
    except requests.HTTPError:
        print(http_error_message + str(response.status_code) + ' ' + response.reason)
    except ConnectionError:
        print(connection_error_message)
    except TimeoutError:
        print(timeout_error_message)
    except ValueError:
        print(invalid_json_message)

# End of Simplifying Functions


# Menu Printers
def print_main_menu():
    clear_screen()
    print('------------------------------------')
    print('OTA Firmware Update'.center(36))
    print('------------------------------------')
    print('0. Quit')
    print('1. Update Firmware')
    print('2. Register Device/Cluster')
    print('3. Delete Device/Cluster')
    print('------------------------------------')

    return 4


def print_update_menu():
    clear_screen()
    print('------------------------------------')
    print('Choose Update Mode'.center(36))
    print('------------------------------------')
    print('0. Return')
    print('1. Update Individual Device')
    print('2. Update Cluster of Device')
    print('------------------------------------')

    return 3


def print_register_menu():
    clear_screen()
    print('------------------------------------')
    print('Choose Register Mode'.center(36))
    print('------------------------------------')
    print('0. Return')
    print('1. Register New Individual Device')
    print('2. Register New Cluster of Device')
    print('3. Add New Device to Cluster')
    print('------------------------------------')

    return 4

# TODO: Add pagination later (also modify the return value)
def print_update_options(items, keyword):
    clear_screen()
    print('------------------------------------')
    print('Choose a {} to Update'.format(keyword).center(36))
    print('------------------------------------')
    print('0. Return')

    ctr = 1

    if len(items) > 0:
        for item in items:
            print('{}. {}'.format(ctr, item['id']))
            ctr += 1
    else:
        print('No {} detected'.format(keyword))

    print('------------------------------------')
    return ctr


def print_free_devices_options(free_devices):
    clear_screen()
    print('------------------------------------')
    print('Choose Device to Add to Cluster'.center(36))
    print('------------------------------------')
    print('0. Return')

    ctr = 1

    if len(free_devices) > 0:
        for device in free_devices:
            print('{}. {}'.format(ctr, device['id']))
            ctr += 1
    else:
        print('No free devices detected!')

    print('------------------------------------')
    return ctr


def print_cluster_options(clusters):
    clear_screen()
    print('------------------------------------')
    print('Choose the Cluster'.center(36))
    print('------------------------------------')
    print('0. Return')

    ctr = 1

    if len(clusters) > 0:
        for cluster in clusters:
            print('{}. {}'.format(ctr, cluster['id']))
            ctr += 1
    else:
        print('No clusters to choose from')

    print('------------------------------------')
    return ctr

# End of Menu Printers

def cli_ota_app():
    while True:
        max_main_menu_input = print_main_menu()

        try:
            main_input = int(input(input_prompt))

            if main_input not in range(max_main_menu_input):
                raise ValueError

        except ValueError:
            handle_misinput()
            continue

        else:
            if main_input == 0:
                # Quit Option
                print('Thank you!')
                break

            elif main_input == 1:
                # Firmware Update Option
                while True:
                    max_update_menu_input = print_update_menu()

                    try:
                        update_input = int(input(input_prompt))

                        if update_input not in range(max_update_menu_input):
                            raise ValueError

                    except ValueError:
                        handle_misinput()
                        continue

                    else:
                        if update_input != 0:
                            # By default, points to cluster option
                            keyword = 'Cluster'
                            data_endpoint = 'list/clusters/'
                            target_url = 'update/cluster/'

                            if update_input == 1:
                                # Point to individual devices mode if previous input == 1
                                keyword = 'Device'
                                data_endpoint = 'list/devices/'
                                target_url = 'update/cluster/'

                            print('Fetching Data from Server...')

                            try:
                                response = requests.get(base_url + data_endpoint)

                                if response.raise_for_status() is None:
                                    items = response.json()['data']

                                    while True:
                                        max_count = print_update_options(
                                            items, keyword)

                                        try:
                                            update_choice = int(
                                                input(input_prompt))

                                            if update_choice not in range(max_count):
                                                raise ValueError

                                        except ValueError:
                                            handle_misinput()
                                            continue
                                        else:
                                            if update_choice != 0:
                                                print(
                                                    'Updating {}...'.format(keyword))

                                                update_endpoint = 'update/device/' if update_input == 1 else 'update/cluster/'

                                                post_data = {
                                                    "id": str(items[update_choice-1]['id'])}
                                                send_to_endpoint(
                                                    update_endpoint, post_data)
                                                getch()
                                            break
                                else:
                                    raise requests.HTTPError
                            except requests.HTTPError:
                                print(
                                    http_error_message + str(response.status_code) + ' ' + response.reason)
                            except ConnectionError:
                                print(connection_error_message)
                            except TimeoutError:
                                print(timeout_error_message)
                            except ValueError:
                                print(invalid_json_message)
                        break
            elif main_input == 2:
                # Register Device Option
                while True:
                    max_register_menu_input = print_register_menu()

                    try:
                        register_input = int(input(input_prompt))

                        if register_input not in range(max_register_menu_input):
                            raise ValueError

                    except ValueError:
                        handle_misinput()
                        continue

                    else:
                        if register_input == 0:
                            break

                        elif register_input == 1:
                            # Register New Device
                            valid_input = False

                            while True:
                                new_device_name = input(input_id_prompt)

                                #  Input Validation
                                if new_device_name == '0':
                                    break
                                elif new_device_name.isidentifier() is False:
                                    print(invalid_identifier_message)
                                elif len(new_device_name) not in range(8, 31):
                                    print(incorrect_length_message)
                                else:
                                    valid_input = True
                                    break

                            if valid_input:
                                print('Registering new Device ID ' + new_device_name)

                                new_device_endpoint = 'new/device/'
                                post_data = {
                                    "id": new_device_name,
                                    "type": None,
                                    "cluster": None,
                                }

                                send_to_endpoint(new_device_endpoint, post_data)
                                getch()
                            else:
                                continue

                        elif register_input == 2:
                            # Register New Cluster
                            valid_input = False

                            while True:
                                new_cluster_name = input(input_id_prompt)

                                #  Input Validation
                                if new_cluster_name == '0':
                                    break
                                elif new_cluster_name.isidentifier() is False:
                                    print(invalid_identifier_message)
                                elif len(new_cluster_name) not in range(8, 31):
                                    print(incorrect_length_message)
                                else:
                                    valid_input = True
                                    break

                            if valid_input:
                                print('Registering new Cluster ID ' +
                                    new_cluster_name)

                                new_cluster_endpoint = 'new/cluster/'
                                post_data = {
                                    "id": new_cluster_name,
                                    "type": None,
                                    "list": [],
                                }

                                send_to_endpoint(new_cluster_endpoint, post_data)
                                getch()
                            else:
                                continue

                        elif register_input == 3:
                            # Add Device to Cluster
                            free_devices_endpoint = 'list/free_devices/'
                            print('Fetching Free Devices List...')

                            try:
                                response = requests.get(
                                    base_url + free_devices_endpoint)

                                if response.raise_for_status() is None:
                                    free_devices = response.json()
                                    while True:
                                        options_count = print_free_devices_options(
                                            free_devices)

                                        try:
                                            free_device_choice = int(
                                                input(input_prompt))

                                            if free_device_choice not in range(options_count):
                                                raise ValueError

                                        except ValueError:
                                            handle_misinput()
                                            continue

                                        else:
                                            if free_device_choice != 0:
                                                cluster_list_endpoint = 'list/clusters/'
                                                print('Fetching Cluster List...')

                                                try:
                                                    new_response = requests.get(
                                                        base_url + cluster_list_endpoint)

                                                    if new_response.raise_for_status() is None:
                                                        clusters = new_response.json()[
                                                            'data']

                                                        while True:
                                                            choice_count = print_cluster_options(
                                                                clusters)

                                                            try:
                                                                cluster_choice = int(
                                                                    input(input_prompt))

                                                                if cluster_choice not in range(choice_count):
                                                                    raise ValueError
                                                            except ValueError:
                                                                handle_misinput()
                                                                continue
                                                            else:
                                                                if cluster_choice != 0:
                                                                    print('Registering Device {} to Cluster {}'.format(
                                                                        free_devices[free_device_choice-1]['id'], clusters[cluster_choice-1]['id']))

                                                                    register_device_endpoint = 'register/device/'
                                                                    patch_data = {
                                                                        "device_id": str(free_devices[free_device_choice-1]['id']),
                                                                        "cluster_id": str(clusters[cluster_choice-1]['id'])
                                                                    }

                                                                    send_to_endpoint(
                                                                        register_device_endpoint, patch_data, method='PATCH')
                                                                    getch()
                                                                break
                                                    else:
                                                        raise requests.HTTPError
                                                except requests.HTTPError:
                                                    print(
                                                        http_error_message + str(new_response.status_code) + ' ' + new_response.reason)
                                                except ConnectionError:
                                                    print(connection_error_message)
                                                except TimeoutError:
                                                    print(timeout_error_message)
                                                except ValueError:
                                                    print(invalid_json_message)
                                            break
                                else:
                                    raise requests.HTTPError
                            except requests.HTTPError:
                                print(
                                    http_error_message + str(response.status_code) + ' ' + response.reason)
                            except ConnectionError:
                                print(connection_error_message)
                            except TimeoutError:
                                print(timeout_error_message)
                            except ValueError:
                                print(invalid_json_message)

            elif main_input == 3:
                # Delete option
                pass

# CLI Entry point
if __name__ == '__main__':
    cli_ota_app()
    return 0