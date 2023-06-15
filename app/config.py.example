import logging

INSTALL_NAME = 'Nombre'                                         # Nombre de la instalación, se incluye en los mensajes de error, para identificar el origen del mensaje

LOG_LEVEL = logging.WARNING

TELEGRAM = {
    'bot-token': 'TOKEN',
    'allowed-groups': [ -10012345678 ],                         # Grupos cuyos usuarios pueden interactuar con el chat
    'allowed-users': [ 12345678 ],                              # Usuarios que pueden interactuar con el chat por privado
    'developer-chat': -10012345678,                             # Chat al que se enviarán los mensajes de error (opcional)
}

MQTT = {
    'broker': {
        'address': '127.0.0.1',                                 # Dirección IP o nombre DNS del broker MQTT
        'port': 1883,                                           # Puerto del broker MQTT
        'username': 'USER',                                     # Usuario con el que poder leer de la cola de MQTT o enviar mensajes
        'password': 'PASSWORD',                                 # Contraseña del usuario MQTT
    },
    'first-reconnect-delay': 1,
    'max-reconned-delay': 120,
    'delay-on-reconnect-multiplier': 2,
    'max-reconnect-attempts': 10,
}

ALARMO = {
    'mqtt-topics': {
        'state': 'alarmo/state',                                
        'command': 'alarmo/command',
    },
    'arm-modes': [ 'arm-home', 'arm-away' ],                    # Los modos de alarma que se pueden configurar desde /alarms (no introducir "disarm")
                                                                # Se soporta: arm-home, arm-away, arm-night y arm-vacation
    'arm-modes-synonyms': {                                     # Palabras clave para usar en /alarms [arm_mode] en lugar de las palabras indicadas en "arm-modes" (opcional)
        'home': 'arm-home',
        'away': 'arm-away',
    },
    'arm-modes-names': {                                        # Nombres de los modos de alarma, en minúsculas (opcional)
        'arm-home': 'casa',
        'arm-away': 'fuera de casa'     
    },
}
    
CAMERAS = {
    'devices': {
        '1': {                                                  # El ID de la cámara solo una palabra (o varias separadas por guiones o guines bajos)
            'name': 'NOMBRE',
            'ip': 'IP',
            'oem': 'tapo',                                      # Fabricante de la cámara (solo "tapo" está soportado actualmente)
        },
    },
    'oems': {
        'tapo': {
            'user': 'USER',                                     # Usuario de acceso a la cámara (es el usuario RSTP que se ha puesto en opciones avanzadas, y si éste no funciona entonces probar "admin")
            'password': 'PASSWORD',                             # Contraseña de acceso a la cámara (es la contraseña del usuario RSTP que se ha puesto en opciones avanzadas, y si ésta no funciona entonces probar la de la cuenta TP-Link)
        },
    },
}
