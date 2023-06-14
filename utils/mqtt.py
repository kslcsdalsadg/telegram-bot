from paho.mqtt import client as mqtt
from time import sleep

import config
import logging

logger = logging.getLogger(__name__)

class MqttAgent():
    DATA = { 'client': None, 'connected': False , 'subscribed-topics': [], 'last-messages': {} }
        
    @staticmethod
    def _subscribe_topics(mqtt_client):
        for topic in MqttAgent.DATA['subscribed-topics']: 
            mqtt_client.subscribe(topic)
        
    @staticmethod
    def _on_message(mqtt_client, userdata, message):
        MqttAgent.DATA['last-messages'][message.topic] = message.payload.decode('utf-8')
    
    @staticmethod
    def _on_disconnect(mqtt_client, userdata, result_code):
        MqttAgent.DATA['connected'] = False
        logging.info('Se ha desconectado del servicio mqtt (códido de error: %)', result_code)
        reconnect_attempt, reconnect_delay = 0, config.MQTT['first-reconnect-delay']
        while reconnect_attempt < config.MQTT['max-reconnect-attempts']:
            logging.info('Esperando %d segundos antes de intentar de reconectar con el servicio mqtt', reconnect_delay)
            sleep(reconnect_delay)
            try:
                mqtt_client.reconnect()
                logging.info("Se ha establecido la conexión con el servicio mqtt")
                return
            except: 
                pass
            reconnect_delay = min(reconnect_delay * config.MQTT['delay-on-reconnect-multiplier'], config.MQTT['max-reconned-delay'])
            reconnect_attempt += 1
        logging.info('No se ha podido conectar con el servicio mqtt tras %d intentos...', reconnect_attempt) 

    @staticmethod
    def _on_connect(mqtt_client, userdata, flags, result_code):
        if result_code != 0: 
            logging.getLogger(__name__).error('No se ha podido conectar con mqtt (códido de error %s)', result_code)
        else: 
            MqttAgent.DATA['connected'] = True
            MqttAgent._subscribe_topics(mqtt_client)       
    
    @staticmethod
    def initialize():
        MqttAgent.DATA['client'] = mqtt.Client()
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
    def subscribe(topic):
        if not topic in MqttAgent.DATA['subscribed-topics']:
            MqttAgent.DATA['subscribed-topics'].append(topic)
            if MqttAgent.is_connected(): 
                MqttAgent.DATA['client'].subscribe(topic)
        
    @staticmethod
    def unsubscribe(topic):
        if topic in MqttAgent.DATA['subscribed-topics']:
            MqttAgent.DATA['subscribed-topics'].remove(topic)
            if MqttAgent.is_connected(): 
                MqttAgent.DATA['client'].unsubscribe(topic)

    @staticmethod
    def send_message(topic, message, retain = False):
        if MqttAgent.is_connected(): 
            MqttAgent.DATA['client'].publish(topic, message, retain = retain)
        
    @staticmethod
    def get_last_message(topic):
        return MqttAgent.DATA['last-messages'][topic] if MqttAgent.is_connected() else None
