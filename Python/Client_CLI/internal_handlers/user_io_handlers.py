# Menu Printers
import os
import platform

from constants import prompts

width = 36
separator = '-' * width

def clear_screen():
    command = 'clear' if platform.system() != 'Windows' else 'cls'
    os.system(command)


def menu_input_validation(options_limit):
    user_input = int(input(prompts.INPUT_PROMPT))

    if user_input not in range(options_limit):
        raise IndexError
    elif user_input == 0:
        return None
    else:
        return user_input


def handle_main_menu():
    clear_screen()
    print(separator)
    print('OTA Firmware Update'.center(36))
    print(separator)
    print('0. Quit')
    print('1. Update Firmware')
    print('2. Register Device/Cluster')
    print('3. Delete Device/Cluster')
    print(separator)
    return menu_input_validation(4)


def handle_update_menu():
    clear_screen()
    print(separator)
    print('Choose Update Mode'.center(36))
    print(separator)
    print('0. Return')
    print('1. Update Individual Device')
    print('2. Update Cluster of Device')
    print(separator)
    return menu_input_validation(3)


def handle_register_menu():
    clear_screen()
    print(separator)
    print('Choose Register Mode'.center(36))
    print(separator)
    print('0. Return')
    print('1. Add New Individual Device')
    print('2. Add New Cluster ')
    print('3. Register Device to Cluster')
    print(separator)
    return menu_input_validation(4)

# TODO: Add pagination later
def handle_options_list(items, title, exhausted):
    clear_screen()
    print(separator)
    print(title.center(36))
    print(separator)
    print('0. Return')
    
    ctr = 1

    if len(items) > 0:
        for item in items:
            print('{}. {}'.format(ctr, item['id']))
            ctr += 1
    else:
        print(exhausted)

    print(separator)
    return menu_input_validation(ctr)


def handle_update_options(items, keyword):
    title = 'Choose a {} to Update'.format(keyword)
    exhausted = 'No {} detected!'.format(keyword)
    user_choice = handle_options_list(items, title, exhausted)
    return None if user_choice is None else items[user_choice - 1]


def handle_free_devices_options(free_devices):
    title = 'Choose Device to Add to Cluster'
    exhausted = 'No free devices detected!'
    user_choice = handle_options_list(free_devices, title, exhausted)
    return None if user_choice is None else free_devices[user_choice - 1]


def handle_cluster_options(clusters):
    title = 'Choose the cluster'
    exhausted = 'No clusters available!'
    user_choice = handle_options_list(clusters, title, exhausted)
    return None if user_choice is None else clusters[user_choice - 1]
