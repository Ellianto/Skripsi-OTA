import keyword

from constants import endpoints, messages, prompts

from internal_handlers import user_io_handlers

from internal_handlers.network_handlers import fetch_from_server, send_to_server
from internal_handlers.error_handlers import handle_misinput

# Internal Menu Handlers
def update_menu_logic():
    while True:
        try:
            update_input = user_io_handlers.handle_update_menu()

            if update_input is None:
                break

            print('Fetching Data from Server...')
            target_endpoint = endpoints.LIST_DEVICES if update_input == 1 else endpoints.LIST_CLUSTERS
            items_json = fetch_from_server(target_endpoint)

            if items_json is not None:
                update_options_logic(items_json['data'], update_input)

            break
        except Exception as err:
            handle_misinput(err)


def update_options_logic(items, menu_input):
    item_name = 'Device' if menu_input == 1 else 'Cluster'

    while True:
        try:
            update_choice = user_io_handlers.handle_update_options(items, item_name)

            if update_choice is None:
                break

            print('Updating {} with ID {}...'.format(
                item_name, update_choice['id']))

            update_endpoint = endpoints.UPDATE_DEVICE if menu_input == 1 else endpoints.UPDATE_CLUSTER
            post_data = {'id': str(update_choice['id'])}

            send_to_server(update_endpoint, post_data)
            break
        except Exception as err:
            handle_misinput(err)


def register_menu_logic():
    while True:
        try:
            register_input = user_io_handlers.handle_register_menu()

            if register_input is None:
                break
            elif register_input in [1, 2]:  # Add new Device/Cluster
                new_item_options_logic(register_input)
            elif register_input == 3:  # Add Device to Cluster
                print('Fetching Free Devices List...')
                free_devices_endpoint = endpoints.LIST_FREE_DEVICES
                free_devices_json = fetch_from_server(free_devices_endpoint)

                if free_devices_json is not None:
                    free_device_options_logic(free_devices_json['data'])

        except Exception as err:
            handle_misinput(err)


def new_item_options_logic(menu_input):
    valid_input = False

    while valid_input is False:
        new_item_id = input(prompts.INPUT_ID_PROMPT)

        if new_item_id == '0':
            break
        elif new_item_id.isidentifier() is False or keyword.iskeyword(new_item_id) is True:
            print(messages.INVALID_IDENTIFIER_MESSAGE)
        elif len(new_item_id) not in range(8, 31):
            print(messages.INCORRECT_LENGTH_MESSAGE)
        else:
            valid_input = True

    if valid_input is True:
        item_name = 'Device' if menu_input == 1 else 'Cluster'
        print('Registering new {} ID {}'.format(item_name, new_item_id))

        target_endpoint = endpoints.NEW_DEVICE if menu_input == 1 else endpoints.NEW_CLUSTER
        post_data = {"id": str(new_item_id)}

        send_to_server(target_endpoint, post_data)


def free_device_options_logic(free_devices):
    while True:
        try:
            free_device_choice = user_io_handlers.handle_free_devices_options(free_devices)

            if free_device_choice is None:
                break

            print('Fetching Cluster List...')
            cluster_list_endpoint = endpoints.LIST_CLUSTERS
            clusters_json = fetch_from_server(cluster_list_endpoint)

            if clusters_json is not None:
                clusters = clusters_json['data']
                choose_cluster_options_logic(clusters, free_device_choice)

            break

        except Exception as err:
            handle_misinput(err)


def choose_cluster_options_logic(clusters, free_device_choice):

    while True:
        try:
            cluster_choice = user_io_handlers.handle_cluster_options(clusters)

            if cluster_choice is None:
                break

            print('Registering Device {} to Cluster {}...'.format(
                free_device_choice['id'], cluster_choice['id']))
            
            register_device_endpoint = endpoints.REGISTER_DEVICE
            patch_data = {
                "device_id": str(free_device_choice['id']),
                "cluster_id": str(cluster_choice['id'])
            }

            send_to_server(register_device_endpoint, patch_data, method='PATCH')
            break
        except Exception as err:
            handle_misinput(err)

# TODO: Add logic for deleting device/cluster later
def delete_menu_logic():
    pass
# End of Internal Menu Handlers
