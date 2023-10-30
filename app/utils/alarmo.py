from utils.mqtt import MqttAgent
from time import sleep

from utils.mqtt import MqttAgent

import logging
import config
import json

logger = logging.getLogger(__name__)

class AlarmoUtils():
    CONFIG = { 'default-timeout-for-commands': 15 }

    @staticmethod
    def initialize():
        MqttAgent.subscribe(config.ALARMO['mqtt-topics']['state'])

    @staticmethod
    def can_change_state():
        return MqttAgent.is_connected() and (MqttAgent.get_last_message(config.ALARMO['mqtt-topics']['state']) is not None)

    @staticmethod
    def get_state():
        return MqttAgent.get_last_message(config.ALARMO['mqtt-topics']['state'])

    @staticmethod
    def send_command(command, requested_state, timeout = 0, do_not_bypass_open_sensors = False):
        timeout = AlarmoUtils.CONFIG['default-timeout-for-commands'] if timeout <= 0 else timeout
        if MqttAgent.is_connected():
            payload = { 'command': command, 'skip_delay': True }
            if command != 'DISARM' and not do_not_bypass_open_sensors:
                payload['bypass_open_sensors'] = True
            MqttAgent.send_message(config.ALARMO['mqtt-topics']['command'], json.dumps(payload))
            for i in range(timeout):
                sleep(1)
                if (requested_state is not None) and (AlarmoUtils.get_state() == requested_state):
                    return True
        return False


