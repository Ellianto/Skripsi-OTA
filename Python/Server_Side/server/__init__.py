from flask import Flask
from flask_mqtt import Mqtt

import os
import json

from pathlib import Path

# Double parent because of "package" structure
# Imported in constants.py
ROOT_DIR = Path(__file__).parent.parent.absolute()

# TODO: Handle delete event for gateway/controller side later
# TODO: Handle disconnect event, if possible later

import server.constants as constants

def init_files():
    init_data = {"data": []}
    files = constants.paths.FILE_LIST
    for file in files:
        if file.exists() is not True:
            with file.open(mode='w') as json_file:
                json.dump(init_data, json_file, indent=4, ensure_ascii=True)


def init_dirs():
    dirs = constants.paths.DIR_LIST
    for dir in dirs:
        if dir.exists() is not True:
            dir.mkdir(parents=True)


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    init_dirs()
    init_files()

    return app

app = create_app()

app.config['MQTT_CLIENT_ID'] = constants.mqtt.MQTT_CLIENT_ID
app.config['MQTT_BROKER_URL'] = constants.mqtt.MQTT_BROKER_URL
app.config['MQTT_BROKER_PORT'] = constants.mqtt.MQTT_BROKER_PORT
app.config['MQTT_KEEPALIVE'] = constants.mqtt.MQTT_KEEPALIVE
app.config['MQTT_TLS_ENABLED'] = constants.mqtt.MQTT_TLS_ENABLED

mqtt_client = Mqtt(app)

import server.routes
import server.internal_handlers