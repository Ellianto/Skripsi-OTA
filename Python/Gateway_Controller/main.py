import json
from pathlib import Path
from subprocess import PIPE

import psutil

import paho.mqtt.client as mqtt
import requests
from voluptuous import All, Coerce, Match, MultipleInvalid, Required, Optional, Schema

http_error_message = 'HTTP Request Failed! HTTP Error Code '
connection_error_message = 'Network Problem! Check your (or the server\'s) network connection!'
timeout_error_message = 'Request Timed Out! Please try again!'
invalid_json_message = 'Invalid JSON Response From Server!'

# To use in conjunction with hosts file
# server = 'http://skripsi_server'
server_base_url = 'http://192.168.88.169:5000'
# TODO: set this value based on the 'ifconfig' command
bind_address = '192.168.88.169'

curr_dir = Path(__file__).parent.absolute()

conf_file_path = curr_dir / 'config.json'

backup_dir = curr_dir / 'backup_data'
destination_dir = curr_dir / 'main_data'

uftp_dir = curr_dir / 'uftp'

status_file_path = uftp_dir / 'status.txt'
log_file_path = uftp_dir / 'uftp_client_logfile.txt'
path_to_uftp_client_exe = uftp_dir / 'uftpd.exe'

# Voluptuous JSON Validator Schema
configuration_validator = Schema({
    Optional('status') : Coerce(str),
    Required('gateway_uid'): All(Coerce(str), Match(r'^0x[0-9A-F]{8}$')),
    Required('mqtt_topic', default='ota/global') : Coerce(str),
    Required('mqtt_broker', default='broker.hivemq.com') : Coerce(str),
    Required('end_device_multicast_addr', default='230.6.6.1'): All(Coerce(str), Match(r'^(22[4-9]|230)(.([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])){3}$')),
    Required('max_log_size', default='2') :  All(Coerce(str), Match(r'^\d{1,2}$')),
    Required('max_log_count', default='5') : All(Coerce(str), Match(r'^\d{1,2}$'))
})

mqtt_client = None

# Initializer Functions

def init_conf(retries=2):
    conf_ready = False
    attempts = 0

    while attempts <= retries and conf_ready is False:
        attempts += 1

        try:
            if conf_file_path.exists() is not True:
                response = requests.get(server_base_url + init_gateway_endpoint)

                if response.raise_for_status() is None:
                    if response.json()['status'] == 'error':
                        continue

                    conf_data = configuration_validator(response.json())

                    with conf_file_path.open(mode='w') as conf_file:
                        config = {
                            'mqtt_topic' : conf_data['mqtt_topic'],
                            'mqtt_broker' : conf_data['mqtt_broker'],
                            'gateway_uid' : conf_data['gateway_uid'],
                            'max_log_size' : conf_data['max_log_size'],
                            'max_log_count' : conf_data['max_log_count'],
                            'end_device_multicast_addr' : conf_data['end_device_multicast_addr'],
                        }

                        json.dump(config, conf_file, indent=4,
                                skipkeys=True, sort_keys=True, ensure_ascii=True)

                else:
                    raise requests.HTTPError

            with conf_file_path.open() as conf_file:
                configuration = json.load(conf_file)
                conf_data = configuration_validator(configuration)
                conf_ready = True

        except requests.HTTPError:
            print(http_error_message + str(response.status_code) + ' ' + response.reason)
        except ConnectionError:
            print(connection_error_message)
        except TimeoutError:
            print(timeout_error_message)
        except ValueError:
            print(invalid_json_message)
        except MultipleInvalid:
            print(invalid_json_message)

    return conf_ready

def init_dirs():
    dirs = [destination_dir, backup_dir]

    for dir in dirs:
        if dir.exists() is not True:
            print('Directory {} not detected, creating directory...'.format(str(dir)))
            dir.mkdir(parents=True)
        else:
            print('Directory {} checked, exists'.format(str(dir)))
    def init_conf():
    pass

def init_uftp():
    init_dirs()
    return_code = None

    try:
        proc_name = 'uftpd.exe'
        uftpd_instance = next(proc for proc in psutil.process_iter() if proc.name() == proc_name)
    except StopIteration:
        with conf_file_path.open() as conf_file:
            configurations = json.load(conf_file)

            uftp_client_cmd = [str(path_to_uftp_client_exe), '-d', '-t',
                                '-A', str(backup_dir),
                                '-D', str(destination_dir),
                                '-L', str(log_file_path),
                                '-F', str(status_file_path),
                                '-U', str(configuration['gateway_uid']),
                                '-g', str(configuration['max_log_size']),
                                '-n', str(configuration['max_log_count'])]

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
    try:
        with conf_file_path.open() as conf_file:
            configuration = json.load(conf_file)
            mqtt_client = mqtt.Client(client_id=configuration['gateway_uid'])
            mqtt_client.on_connect = on_mqtt_connect
            mqtt_client.on_message = on_mqtt_message

            mqtt_client.will_set(configuration['mqtt_topic'], payload='will|{}'.format(configuration['gateway_uid']))

            userdata = {
                'gateway_id' : configuration['gateway_id']
            }

            mqtt_client.user_data_set(userdata)
            mqtt_client.connect(configuration['mqtt_broker'])
            return True
    except Exception as err:
        print(err)
        return False

# End of initializers

# LWM2M Functions
def lwm2m_update():
    pass

def end_device_connect_callback():
    pass

def end_device_disconnect_callback():
    pass

# End of LWM2M Functions

# MQTT Functions
def on_mqtt_connect(client, userdata, flags, rc):
    if rc == 0:
        with conf_file_path.open() as conf_file:
            configuration = json.load(conf_file)
            print('Successfully connected to ' + configuration['mqtt_broker'])
            (result, mid) = mqtt_client.subscribe(
                configuration['mqtt_topic'], qos=2)

    elif rc == 1:
        print('Incorrect Protocol Version detected when connecting to MQTT Broker')
    elif rc == 2:
        print('Invalid Client ID detected when connecting to MQTT Broker')
    elif rc == 3:
        print('MQTT Server/Broker is unavailable when connecting to MQTT Broker')
    elif rc == 4:
        print('Bad Username/Password detected when connecting to MQTT Broker')
    elif rc == 5:
        print('Failed to Authorize when connecting to MQTT Broker')
    else:
        print('Invalid Return Code (' + str(rc) +
                ') when connecting to MQTT Broker')


def on_mqtt_message(client, userdata, msg):
    print("Message Received from topic " + str(
        msg.topic) + ' : ' + str(msg.payload.decode()))

    mqtt_message = msg.payload.decode().split('|')

    if mqtt_message[0] == 'update':
        target_id = str(mqtt_message[2])

        if mqtt_message[1] == 'cluster':
            pass
        elif mqtt_message[1] == 'device':
            pass
# End of MQTT Functions

if __name__ == '__main__':
    if init_conf() is not True:
        print('Error while getting configuration from Server!')
    elif init_uftp() is not in [0, 1]:
        print('Error while starting UFTP Client Daemon!')
    elif init_lwm2m() is not True:
        print('Error while initializing LWM2M Server!')
    elif init_mqtt() is not True:
        print('Error while initializing MQTT Client!')
    else:
        mqtt_client.loop_forever()
