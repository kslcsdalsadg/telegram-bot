from paho.mqtt import client as mqtt
from time import sleep

import config
import logging

logger = logging.getLogger(__name__)

class MqttAgent():
    DATA = { 'client': None, 'connected': False , 'subscribed-topics': {} }
    CONFIG = { 'callback_version': mqtt.CallbackAPIVersion.VERSION2 }

    @staticmethod
    def _subscribe_topics(client):
        for topic in MqttAgent.DATA['subscribed-topics']:
            client.subscribe(topic)

    @staticmethod
    def _on_message(client, userdata, message):
        """
        Callback signature doesn't depends on API version:

            _on_message(client, userdata, message)

        """
        if message.topic in MqttAgent.DATA['subscribed-topics']:
            MqttAgent.DATA['subscribed-topics'][message.topic]['last-message'] = message.payload.decode('utf-8')
            for callback in MqttAgent.DATA['subscribed-topics'][message.topic]['callbacks']:
                callback(MqttAgent.DATA['subscribed-topics'][message.topic]['last-message'])

    @staticmethod
    def _on_disconnect(client, userdata, p1 = None, p2 = None, p3 = None):
        """
        Callback signatures:

        API version 2:
            _on_disconnect(client, userdata, flags, reason_code, properties)

        API version 1:
          For MQTT v3.1 and v3.1.1 it's::
              _on_disconnect(client, userdata, reason_code)

          For MQTT it's v5.0::
              _on_disconnect(client, userdata, reason_code, properties)
        """
        if MqttAgent.CONFIG['callback_version'] == mqtt.CallbackAPIVersion.VERSION2: flags = p1
        reason_code = p2 if MqttAgent.CONFIG['callback_version'] == mqtt.CallbackAPIVersion.VERSION2 else p1
        propierties = p3 if MqttAgent.CONFIG['callback_version'] == mqtt.CallbackAPIVersion.VERSION2 else p2
        MqttAgent.DATA['connected'] = False
        logging.info('Se ha desconectado del servicio mqtt (códido de error: %)', reason_code)
        reconnect_attempt, reconnect_delay = 0, config.MQTT['first-reconnect-delay']
        while reconnect_attempt < config.MQTT['max-reconnect-attempts']:
            logging.info('Esperando %d segundos antes de intentar de reconectar con el servicio mqtt', reconnect_delay)
            sleep(reconnect_delay)
            try:
                client.reconnect()
                logging.info("Se ha establecido la conexión con el servicio mqtt")
                return
            except:
                pass
            reconnect_delay = min(reconnect_delay * config.MQTT['delay-on-reconnect-multiplier'], config.MQTT['max-reconned-delay'])
            reconnect_attempt += 1
        logging.info('No se ha podido conectar con el servicio mqtt tras %d intentos...', reconnect_attempt)

    @staticmethod
    def _on_connect(client, userdata, flags, reason_code, propierties = None):
        """
        Callback signatures:

        API version 2::
            _on_connect(client, userdata, flags, reason_code, properties)

        API version 1:
          For MQTT v3.1 and v3.1.1 it's::
            _on_connect(client, userdata, flags, reason_code)

          For MQTT it's v5.0::
            _on_connect(client, userdata, flags, reason_code, properties)
        """

        if reason_code != 0:
            logging.getLogger(__name__).error('No se ha podido conectar con mqtt (códido de error %s)', reason_code)
        else:
            MqttAgent.DATA['connected'] = True
            MqttAgent._subscribe_topics(client)

    @staticmethod
    def initialize():
        MqttAgent.DATA['client'] = mqtt.Client(MqttAgent.CONFIG['callback_version'])
        MqttAgent.DATA['client'].enable_logger(logging.getLogger(__name__))
        MqttAgent.DATA['client'].username_pw_set(config.MQTT['broker']['username'], config.MQTT['broker']['password'])
        MqttAgent.DATA['client'].on_connect = MqttAgent._on_connect
        MqttAgent.DATA['client'].on_disconnect = MqttAgent._on_disconnect
        MqttAgent.DATA['client'].on_message = MqttAgent._on_message
        MqttAgent.DATA['client'].connect(config.MQTT['broker']['address'], config.MQTT['broker']['port'])
        MqttAgent.DATA['client'].loop_start()

    @staticmethod
    def is_connected():
        return MqttAgent.DATA['connected']

    @staticmethod
    def subscribe(topic, callback = None):
        if topic not in MqttAgent.DATA['subscribed-topics']:
            MqttAgent.DATA['subscribed-topics'][topic] = { 'count': 0, 'last-message': None, 'callbacks': [] }
            if MqttAgent.is_connected():
                MqttAgent.DATA['client'].subscribe(topic)
        MqttAgent.DATA['subscribed-topics'][topic]['count'] += 1
        if callback is not None and callback not in MqttAgent.DATA['subscribed-topics'][topic]['callbacks']:
            MqttAgent.DATA['subscribed-topics'][topic]['callbacks'].append(callback)

    @staticmethod
    def unsubscribe(topic, callback = None):
        if topic in MqttAgent.DATA['subscribed-topics']:
            if callback is not None and callback in MqttAgent.DATA['subscribed-topics'][topic]['callbacks']:
                MqttAgent.DATA['subscribed-topics'][topic]['callbacks'].remove(callback)
            MqttAgent.DATA['subscribed-topics']['count'] -= 1
            if MqttAgent.DATA['subscribed-topics']['count'] == 0:
                if MqttAgent.is_connected():
                    MqttAgent.DATA['client'].unsubscribe(topic)
                MqttAgent.DATA['subscribed-topics'].pop(topic)

    @staticmethod
    def send_message(topic, message, retain = False):
        if MqttAgent.is_connected():
            MqttAgent.DATA['client'].publish(topic, message, retain = retain)

    @staticmethod
    def get_last_message(topic):
        return MqttAgent.DATA['subscribed-topics'][topic]['last-message'] if MqttAgent.is_connected() and topic in MqttAgent.DATA['subscribed-topics'] else None

