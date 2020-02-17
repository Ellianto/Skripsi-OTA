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

    return None if user_input == 0 else user_input

def menu_printer(title, choices):
    clear_screen()
    print(separator)
    print(title.center(width))
    print(separator)

    for choice in choices:
        print(choice)

    print(separator)
    return menu_input_validation(len(choices))


def handle_main_menu():
    title = 'OTA Firmware Update'
    choices = [ '0. Quit',
                '1. Update Firmware',
                '2. Register Device/Cluster',
                '3. Delete Device/Cluster']
    return menu_printer(title, choices)


def handle_update_menu():
    title = 'Choose Update Mode'
    choices = [ '0. Return',
                '1. Update Individual Device',
                '2. Update Cluster of Device']
    return menu_printer(title, choices)


def handle_register_menu():
    title = 'Choose Register Mode'
    choices = [ '0. Return',
                '1. Create New Device ID',
                '2. Create New Cluster ID',
                '3. Register Device ID to Cluster ID']
    return menu_printer(title, choices)

# TODO: Add pagination later
def handle_options_list(items, title, exhausted):
    clear_screen()
    print(separator)
    print(title.center(width))
    print(separator)
    print('0. Return')
    
    ctr = 1
    for item in items:
        print('{}. {}'.format(ctr, item['id']))
        ctr += 1
    
    if len(items) == 0:
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
