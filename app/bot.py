from telegram import Update, ChatMember, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.constants import ParseMode, ChatType
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, InvalidCallbackData, ChatMemberHandler
from datetime import datetime
from time import sleep, time

from utils.docker import DockerUtils
from utils.mqtt import MqttAgent
from utils.alarmo import AlarmoUtils
from utils.camera import CameraUtils
from utils.whats_my_ip import WhatsMyIp

import config

import traceback
import logging
import html
import json
import os

VERSION = '1.0'

ALARMO_ACTIONS = {
    'arm-home': { 'name': 'en casa', 'command': 'ARM_HOME', 'state': 'armed_home' },
    'arm-away': {'name': 'fuera de casa', 'command': 'ARM_AWAY', 'state': 'armed_away'},
    'arm-night': {'name': 'noche', 'command': 'ARM_NIGHT', 'state': 'armed_night'},
    'arm-vacation': {'name': 'vacaciones', 'command': 'ARM_VACATION', 'state': 'armed_vacation'},
    'disarm': { 'command': 'DISARM', 'state': 'disarmed'},
}

DOCKER_ACTIONS = {
    'start': { 'title': 'Iniciar el contenedor', 'action': 'iniciarlo', 'confirm-action': 'iniciar' },
    'stop': {'title': 'Parar el contenedor', 'action': 'pararlo', 'confirm-action': 'parar'},
    'restart': {'title': 'Reiniciar el contenedor', 'action': 'reiniciarlo', 'confirm-action': 'reiniciar' },
    'delete': {'title': 'Eliminar el contenedor', 'action': 'eliminarlo', 'confirm-action': 'eliminar' },
}

BOT_MESSAGES = {}

logger = logging.getLogger(__name__)

##### Funciones auxiliares

def config_block_exists(name):
    return hasattr(config, name)

def get_uptime(get_as_string):
    with open('/proc/uptime', 'r') as file:
        uptime_seconds = float(file.readline().split()[0])
    if not get_as_string:    
        return uptime_seconds  
    a_day, a_hour, a_minute = 24 * 60 * 60, 60 * 60, 60
    uptimes = []
    uptimes.append({ 'value': int(uptime_seconds / a_day), 'description_one': 'día', 'description_other': 'días' })
    uptime_seconds = int(uptime_seconds % a_day)
    uptimes.append({ 'value': int(uptime_seconds / a_hour), 'description_one': 'hora', 'description_other': 'horas' })
    uptime_seconds = int(uptime_seconds % a_hour)
    uptimes.append({ 'value': int(uptime_seconds / a_minute), 'description_one': 'minuto', 'description_other': 'minutos' })
    uptimes.append({ 'value': int(uptime_seconds % a_minute), 'description_one': 'segundo', 'description_other': 'segundos' })
    strings = []
    for i in range(len(uptimes)):
        if uptimes[i]['value'] or ((i == len(uptimes) - 1) and (len(strings) == 0)):
            strings.append('{} {}'.format(uptimes[i]['value'], uptimes[i]['description_one'] if uptimes[i]['value'] == 1 else uptimes[i]['description_other']))
    return " y ".join([", ".join(strings[:-1]), strings[-1]]) if len(strings) > 1 else strings[0] 

##### Gestión de errores Telegram

async def error_handler(update, context):
    logger.error('Se ha producido una excepción al procesar un mensaje: ', exc_info = context.error)
    if ('developer-chat' in config.TELEGRAM) and (config.TELEGRAM['developer-chat'] != 0):
        traceback_string = "".join(traceback.format_exception(None, context.error, context.error.__traceback__))
        message = (
            'Se ha producido un error procesando un mensaje en la instalación de "{}"'.format(config.INSTALL_NAME),
            '<pre>update = {}</pre>'.format(html.escape(json.dumps(update.to_dict() if isinstance(update, Update) else str(update), indent = 2, ensure_ascii = False))),
            '<pre>context.chat_data = {}</pre>'.format(html.escape(str(context.chat_data))),
            '<pre>context.user_data = {}</pre>'.format(html.escape(str(context.user_data))),
            '<pre>{}</pre>'.format(html.escape(traceback_string)),
        )
        await context.bot.send_message(chat_id = config.TELEGRAM['developer-chat'], text = "\n\n".join(message), parse_mode = ParseMode.HTML, disable_notification = True)

##### Funciones auxiliares para Telegram

def get_effective_chat(update):
    if update.message: 
        return update.message.chat
    if update.callback_query: 
        return update.callback_query.message.chat
    return None

def get_effective_user(update):
    if update.message: 
        return update.message.from_user
    if update.callback_query: 
        return update.callback_query.from_user
    return None

def get_callback_data(action, action_modifiers = None, current_callback_data = None):
    callback_data = {}
    if action_modifiers is not None:
        callback_data.update(action_modifiers)
    if current_callback_data is not None:
        callback_data['root-menu'] = current_callback_data['root-menu']
    callback_data['action'] = action
    return callback_data

async def callback_query_answer(update):
    try:
        if update.callback_query:
            await update.callback_query.answer()
    except:
        pass

async def send_menu_message(update, text, menu):
    if update.callback_query:
        await update.callback_query.message.edit_text("\n".join(text), parse_mode = ParseMode.HTML, reply_markup = InlineKeyboardMarkup(menu))
    else:
        message = await update.effective_chat.send_message("\n".join(text), parse_mode = ParseMode.HTML, reply_markup = InlineKeyboardMarkup(menu), disable_notification = True)
        if not message.chat.id in BOT_MESSAGES:
            BOT_MESSAGES[message.chat.id] = {}
        BOT_MESSAGES[message.chat.id][message.id] = True

async def delete_menu_message(message):
    await message.delete()
    if message.chat.id in BOT_MESSAGES and message.id in BOT_MESSAGES[message.chat.id]:
        BOT_MESSAGES[message.chat.id].pop(message.id)

##### Gestión de usuarios autorizados

def is_user_allowed_to_interact_with_the_chat(user, chat = None):
    if config.TELEGRAM:
      if (chat is not None) and (chat.type != ChatType.PRIVATE) and (chat.id not in config.TELEGRAM['allowed-groups']): 
          return False
      return (user is not None) and ((str(user.id) in config.TELEGRAM['allowed-users'].keys()) or (user.username in config.TELEGRAM['allowed-users'].keys()))
    return False
    
async def is_user_allowed_to_exec_administrative_commands(user):
    if is_user_allowed_to_interact_with_the_chat(user):
        if str(user.id) in config.TELEGRAM['allowed-users'].keys(): 
            return config.TELEGRAM['allowed-users'][str(user.id)]
        if user.username in config.TELEGRAM['allowed-users'].keys(): 
            return config.TELEGRAM['allowed-users'][user.username]
    return False

##### Mostramos un mensaje cuando se une un nuevo usuario o cuando alguien abandona un grupo

def _extract_status_change(chat_member_update):
    status_change = chat_member_update.difference().get('status')
    old_is_member, new_is_member = chat_member_update.difference().get('is_member', (None, None))
    if status_change is None:
        return None
    old_status, new_status = status_change
    was_member = (old_status in [ ChatMember.MEMBER, ChatMember.OWNER, ChatMember.ADMINISTRATOR ]) or ((old_status == ChatMember.RESTRICTED) and (old_is_member is True))
    is_member = (new_status in [ ChatMember.MEMBER, ChatMember.OWNER, ChatMember.ADMINISTRATOR ]) or ((new_status == ChatMember.RESTRICTED) and (new_is_member is True))
    return was_member, is_member

async def greet_chat_members(update, context):
    result = _extract_status_change(update.chat_member)
    if result is not None:
        text = None
        user = update.chat_member.new_chat_member.user
        was_member, is_member = result
        if not was_member and is_member:
            text = [ 'Hola "{}" ({}), eres bienvenido.'.format(user.mention_html(), user.id), 'Puedes introducir "/menu" para interactuar con el bot...' ]
        elif was_member and not is_member:
            text = [ '"{}" ({}) ha salido del grupo.'.format(user.mention_html(), user.id) ]
        if text is not None:
            await update.effective_chat.send_message("\n\n".join(text), parse_mode = ParseMode.HTML, disable_notification = True)

##### Gestión de menús de Telegram

def _get_go_previous_menu_button_and_text_suggestion(current_menu, data = None):
    action, action_text, text = 'exit', '< Salir', 'pulsa el botón "&lt; Salir" para continuar.'
    root_menu = data['root-menu'] if (data is not None) and ('root-menu' in data) else 'main-menu'
    if current_menu != root_menu:
        action, action_text, text = 'main-menu', '< Atrás', 'pulsa el botón "&lt; Atrás" para volver al menú principal.'
        if current_menu == 'camera-menu':
            action, action_text, text = 'cameras-menu', '< Atrás', 'pulsa el botón "&lt; Atrás" para volver a la lista de cámaras.'
        if current_menu == 'docker-menu':
            action, action_text, text = 'dockers-menu', '< Atrás', 'pulsa el botón "&lt; Atrás" para volver a la lista de contenedores.'
    return InlineKeyboardButton(action_text, callback_data = get_callback_data(action, current_callback_data = data)), text

async def get_main_menu(user, chat, data):
    exit_button, exit_text_suggestion = _get_go_previous_menu_button_and_text_suggestion('main-menu', data)
    menu = []
    if config_block_exists('ALARMO') and AlarmoUtils.can_change_state():
        menu.append([ InlineKeyboardButton('Gestiona tu alarma', callback_data = get_callback_data('alarm-menu', current_callback_data = data)) ])
    if await is_user_allowed_to_exec_administrative_commands(user):
        if config_block_exists('CAMERAS') and 'devices' in config.CAMERAS:
            menu.append([ InlineKeyboardButton('Gestiona tus cámaras', callback_data = get_callback_data('cameras-menu', current_callback_data = data)) ])
        if config_block_exists('DOCKERS'):
            menu.append([ InlineKeyboardButton('Gestiona tus contenedores', callback_data = get_callback_data('dockers-menu', current_callback_data = data)) ])
        if config_block_exists('VPN'):
            menu.append([InlineKeyboardButton('Gestiona tu VPN', callback_data=get_callback_data('vpn-menu', current_callback_data = data))])
    menu.append([ InlineKeyboardButton('Muestra la IP pública del router', callback_data = get_callback_data('whats-my-ip', current_callback_data = data)) ])
    menu.append([ InlineKeyboardButton('Muestra el tiempo transcurrido desde el último reinicio', callback_data = get_callback_data('uptime', current_callback_data = data)) ])
    text = [ 'Selecciona una opción para continuar o {}'.format(exit_text_suggestion) ]
    menu.append([ exit_button ])
    return menu, text

def _get_alarmo_arm_mode_name(arm_mode):
    return config.ALARMO['arm-modes-names'][arm_mode] if ('arm-modes-names' in config.ALARMO) and (arm_mode in config.ALARMO['arm-modes-names']) else ALARMO_ACTIONS[arm_mode]['name']

async def get_alarm_menu(user, chat, data):
    back_button, back_text_suggestion = _get_go_previous_menu_button_and_text_suggestion('alarm-menu', data)
    menu, text = [], [ 'Se ha restringido el acceso a esta funcionalidad en el archivo de configuración.', '', back_text_suggestion.capitalize() ]
    if config_block_exists('ALARMO'):
        text = ['Ahora mismo no se puede interactuar con tu alarma.', '', back_text_suggestion.capitalize()]
        if AlarmoUtils.can_change_state():
            if AlarmoUtils.get_state() == 'disarmed':
                for arm_mode in config.ALARMO['arm-modes']:
                    if arm_mode in ALARMO_ACTIONS:
                        menu.append([ InlineKeyboardButton('Conecta la alarma en modo "{}"'.format(_get_alarmo_arm_mode_name(arm_mode)), callback_data = get_callback_data('set-alarm-arm-mode', action_modifiers = { 'arm-mode': arm_mode }, current_callback_data = data)) ])
            else:
                menu.append([ InlineKeyboardButton('Desconecta la alarma', callback_data = get_callback_data('set-alarm-arm-mode', action_modifiers = { 'arm-mode': 'disarm' }, current_callback_data = data)) ])
            text = [ 'Te mostramos las opciones de gestión de tu alarma.', '', 'Haz clic en una o {}'.format(back_text_suggestion) ]
    menu.append([ back_button ])
    return menu, text

async def get_cameras_menu(user, chat, data):
    back_button, back_text_suggestion = _get_go_previous_menu_button_and_text_suggestion('cameras-menu', data)
    menu, text = [], [ 'No tienes permiso para acceder a esta funcionalidad.', '', back_text_suggestion.capitalize() ]
    if await is_user_allowed_to_exec_administrative_commands(user):
        text = ['Se ha restringido el acceso a esta funcionalidad en el archivo de configuración.', '', back_text_suggestion.capitalize()]
        if config_block_exists('CAMERAS'):
            cameras = []
            if 'devices' in config.CAMERAS:
                for camera_id in config.CAMERAS['devices'].keys():
                    cameras.append({ 'id': camera_id, 'name': config.CAMERAS['devices'][camera_id]['name'] })
            for camera_data in sorted(cameras, key = lambda camera_data: camera_data['name']):
                menu.append([ InlineKeyboardButton(camera_data['name'], callback_data = get_callback_data('camera-menu', action_modifiers = { 'camera-id': camera_data['id'] }, current_callback_data = data)) ])
            text = [ 'Te mostramos la lista de cámaras.', '', 'Haz clic en la ubicación de cualquiera de ellas para ver las opciones disponibles o {}'.format(back_text_suggestion) ] if len(menu) > 0 else [ 'No hay cámaras disponibles.', '', back_text_suggestion.capitalize() ]
    menu.append([ back_button ])
    return menu, text

async def get_camera_menu(user, chat, data):
    back_button, back_text_suggestion = _get_go_previous_menu_button_and_text_suggestion('camera-menu', data)
    menu, text = [], [ 'No tienes permiso para acceder a esta funcionalidad.', '', back_text_suggestion.capitalize() ]
    if await is_user_allowed_to_exec_administrative_commands(user):
        text = [ 'Se ha restringido el acceso a esta funcionalidad en el archivo de configuración.', '', back_text_suggestion.capitalize() ]
        if config_block_exists('CAMERAS'):
            camera_data = config.CAMERAS['devices'][data['camera-id']] if ('devices' in config.CAMERAS) and (data['camera-id'] in config.CAMERAS['devices']) else None
            if camera_data is not None:
                menu.append([ InlineKeyboardButton('Reiniciar la cámara', callback_data = get_callback_data('interact-with-a-camera', action_modifiers = { 'camera-id': data['camera-id'], 'command': 'restart' }, current_callback_data = data)) ])
            text = [ 'La dirección IP asociada a la cámara "{}" es la "{}.".'.format(camera_data['name'], camera_data['ip']), '', 'Haz clic sobre la acción a ejecutar o {}'.format(back_text_suggestion) ] if camera_data is not None else [ 'La cámara que has indicado no existe o no es accesible para este bot.', '', back_text_suggestion.capitalize() ]
    menu.append([ back_button ])
    return menu, text

async def get_dockers_menu(user, chat, data):
    back_button, back_text_suggestion = _get_go_previous_menu_button_and_text_suggestion('dockers-menu', data)
    menu, text = [], [ 'No tienes permiso para acceder a esta funcionalidad.', '', back_text_suggestion.capitalize() ]
    if await is_user_allowed_to_exec_administrative_commands(user):
        text = [ 'Se ha restringido el acceso a esta funcionalidad en el archivo de configuración.', '', back_text_suggestion.capitalize() ]
        if config_block_exists('DOCKERS'):
            for container in sorted(DockerUtils.get_containers(True), key = lambda container: container.name):
                menu.append([ InlineKeyboardButton(container.name, callback_data = get_callback_data('docker-menu', action_modifiers = { 'docker-id': container.id }, current_callback_data = data)) ])
            text = [ 'Te mostramos la lista de contenedores.', '', 'Haz clic en el nombre de cualquiera de ellos para ver las opciones disponibles o {}'.format(back_text_suggestion) ]
            menu.append([ InlineKeyboardButton('Recargar', callback_data = get_callback_data('dockers-menu', current_callback_data = data)), back_button ])
    if len(menu) == 0:
        menu.append([ back_button ])
    return menu, text

async def get_docker_menu(user, chat, data):
    back_button, back_text_suggestion = _get_go_previous_menu_button_and_text_suggestion('docker-menu', data)
    menu, text = [], [ 'No tienes permiso para acceder a esta funcionalidad.', '', back_text_suggestion.capitalize() ]
    if await is_user_allowed_to_exec_administrative_commands(user):
        text = [ 'Se ha restringido el acceso a esta funcionalidad en el archivo de configuración.', '', back_text_suggestion.capitalize() ]
        if config_block_exists('DOCKERS'):
            text = [ 'El contenedor indicado no se encuentra.', '', back_text_suggestion.capitalize() ]
            if DockerUtils.container_exists(data['docker-id']):
                name, is_running = DockerUtils.get_container_name(data['docker-id']), DockerUtils.is_container_running(data['docker-id'])
                if is_running:
                    menu.append([ InlineKeyboardButton(DOCKER_ACTIONS['stop']['title'], callback_data = get_callback_data('interact-with-a-docker', action_modifiers = { 'docker-id': data['docker-id'], 'command': 'stop' }, current_callback_data = data)) ])
                    menu.append([ InlineKeyboardButton(DOCKER_ACTIONS['restart']['title'], callback_data = get_callback_data('interact-with-a-docker', action_modifiers = { 'docker-id': data['docker-id'], 'command': 'restart' }, current_callback_data = data)) ])
                else:
                    menu.append([ InlineKeyboardButton(DOCKER_ACTIONS['start']['title'], callback_data = get_callback_data('interact-with-a-docker', action_modifiers = { 'docker-id': data['docker-id'], 'command': 'start' }, current_callback_data = data)) ])
                    menu.append([ InlineKeyboardButton(DOCKER_ACTIONS['delete']['title'], callback_data = get_callback_data('interact-with-a-docker', action_modifiers = { 'docker-id': data['docker-id'], 'command': 'delete' }, current_callback_data = data)) ])
                text = [ 'El contenedor "{}" {}.'.format(name, 'se está ejecutando' if is_running else 'no se está ejecutando'), '', 'Haz clic sobre la opción deseada o {}'.format(back_text_suggestion) ]
    menu.append([ back_button ])
    return menu, text

async def get_vpn_menu(user, chat, data):
    back_button, back_text_suggestion = _get_go_previous_menu_button_and_text_suggestion('vpn-menu', data)
    menu, text = [], [ 'No tienes permiso para acceder a esta funcionalidad.', '', back_text_suggestion.capitalize() ]
    if await is_user_allowed_to_exec_administrative_commands(user):
        text = [ 'Se ha restringido el acceso a esta funcionalidad en el archivo de configuración.', '', back_text_suggestion.capitalize() ]
        if config_block_exists('VPN'):
            if 'type' in config.VPN:
                if config.VPN['type'] == 'docker' and 'docker' in config.VPN:
                    is_running = DockerUtils.is_container_running(config.VPN['docker'])
                    menu.append([ InlineKeyboardButton('Apagar' if is_running else 'Encender', callback_data = get_callback_data('interact-with-the-vpn', action_modifiers = { 'command': 'stop' if is_running else 'start' }, current_callback_data = data)) ])
                    text = [ 'La VPN está {}.'.format('encendida' if is_running else 'apagada'), '', 'Haz clic sobre la opción deseada o {}'.format(back_text_suggestion) ]
    menu.append([ back_button ])
    return menu, text

async def _menu(update, context, data):
    user, chat = get_effective_user(update), get_effective_chat(update)
    menu, text = [], []
    if not is_user_allowed_to_interact_with_the_chat(user, chat):
        exit_button, exit_text_suggestion = _get_go_previous_menu_button_and_text_suggestion('main-menu')
        menu, text = [ [ exit_button ] ], [ 'No tienes permiso para usar este bot.', '', exit_text_suggestion.capitalize() ]
    elif data['action'] == 'main-menu':
        menu, text = await get_main_menu(user, chat, data)
    elif data['action'] == 'alarm-menu':
        menu, text = await get_alarm_menu(user, chat, data)
    elif data['action'] == 'cameras-menu':
        menu, text = await get_cameras_menu(user, chat, data)
    elif data['action'] == 'camera-menu':
        menu, text = await get_camera_menu(user, chat, data)
    elif data['action'] == 'dockers-menu':
        menu, text = await get_dockers_menu(user, chat, data)
    elif data['action'] == 'docker-menu':
        menu, text = await get_docker_menu(user, chat, data)
    elif data['action'] == 'vpn-menu':
        menu, text = await get_vpn_menu(user, chat, data)
    await callback_query_answer(update)
    await send_menu_message(update, text, menu)

##### Puntos de entrada de los diferentes menús

async def menu(update, context):
    if update.message:
        await update.message.delete()
    await _menu(update, context, update.callback_query.data if update.callback_query else { 'action': 'main-menu', 'root-menu': 'main-menu' })

async def alarm_menu(update, context):
    await update.message.delete()
    if config_block_exists('ALARMO') and len(context.args) != 0:
        arm_mode = ' '.join(context.args).strip()
        if 'arm-modes-synonyms' in config.ALARMO and arm_mode in config.ALARMO['arm-modes-synonyms']:
            arm_mode = config.ALARMO['arm-modes-synonyms'][arm_mode]
        await _set_alarm_arm_mode(update, context, { 'action': 'set-alarm-arm-mode', 'arm-mode': 'disarm' if arm_mode == 'off' else arm_mode })
    else:
        await _menu(update, context, { 'action': 'alarm-menu', 'root-menu': 'alarm-menu' })

async def cameras_menu(update, context):
    await update.message.delete()
    await _menu(update, context, { 'action': 'cameras-menu', 'root-menu': 'cameras-menu' })

async def dockers_menu(update, context):
    await update.message.delete()
    await _menu(update, context, { 'action': 'dockers-menu', 'root-menu': 'dockers-menu' })

async def vpn_menu(update, context):
    await update.message.delete()
    await _menu(update, context, { 'action': 'vpn-menu', 'root-menu': 'vpn-menu' })

def is_menu_request(data):
    return isinstance(data, dict) and 'action' in data and data['action'].endswith('-menu')

##### Lista comandos

async def list_commands(update, context):
    messages = {
        '': [
            'A continuación enumeramos los comandos disponibles:',
            '',
            '<u>General</u>',
            '',
            '<b>/menu</b>: Muestra el menú general',
            '<b>/whatsmyip</b>: Muestra la IP pública del router',
            '<b>/uptime</b>: Muestra el tiempo desde el último reinicio',
        ],
        'alarm': [
            '<u>Gestión de la alarma:</u>',
            '',
            '<b>/alarm</b> : Muestra el menú de la alarma',
            '',
            '<b>/alarm off</b> : Desconecta la alarma',
        ],
        'cameras': [
            '<u>Gestión de las cámaras:</u>',
            '',
            '<b>/cameras</b> : Muestra el menú de cámaras',
        ],
        'dockers': [
            '<u>Gestión de los dockers:</u>',
            '',
            '<b>/dockers</b> : Muestra el menú de dockers',
        ],
        'vpn': [
            '<u>Gestión de la VPN:</u>',
            '',
            '<b>/vpn</b> : Muestra el menú de la VPN',
            '',
            '<b>/vpn on</b> : Enciende la VPN',
            '<b>/vpn off</b> : Apaga la VPN',
        ],
    }
    text = "\n".join(messages[''])
    if config_block_exists('ALARMO'):
        if 'arm-modes' in config.ALARMO:
            messages['alarm'].append('')
            for arm_mode in config.ALARMO['arm-modes']:
                messages['alarm'].append('<b>/alarm {}</b> : Conecta la alarma en modo "{}"'.format(arm_mode, _get_alarmo_arm_mode_name(arm_mode)))
            messages['alarm'].append('')
            if 'arm-modes-synonyms' in config.ALARMO:
                for arm_mode in config.ALARMO['arm-modes-synonyms'].keys():
                    messages['alarm'].append('<b>/alarm {}</b> : Conecta la alarma en modo "{}"'.format(arm_mode, _get_alarmo_arm_mode_name(config.ALARMO['arm-modes-synonyms'][arm_mode])))
        text += "\n\n" + "\n".join(messages['alarm'])
    user, chat = get_effective_user(update), get_effective_chat(update)
    if await is_user_allowed_to_exec_administrative_commands(user):
        if config_block_exists('CAMERAS') and 'devices' in config.CAMERAS:
            messages['cameras'].append('')
            for camera_id in config.CAMERAS['devices']:
                messages['cameras'].append('<b>/camera {} {}</b> : Reinicia la cámara "{}"'.format(camera_id, 'restart', config.CAMERAS['devices'][camera_id]['name']))
            text += "\n\n" + "\n".join(messages['cameras'])
        if config_block_exists('DOCKERS'):
            text += "\n\n" + "\n".join(messages['dockers'])
        if config_block_exists('VPN'):
            text += "\n\n" + "\n".join(messages['vpn'])
    await update.message.delete()
    await update.effective_chat.send_message(text, parse_mode = ParseMode.HTML, disable_notification = True)

##### Confirma una acción antes de ejecutarla

def _is_confirmed(config_ref, name, data):
    return ('bypassed-confirmations' in config_ref and name in config_ref['bypassed-confirmations'] and config_ref['bypassed-confirmations'][name]) or ('action-confirmed' in data) 
    
async def _confirm(update, description, data):
    delete_message = False if update.callback_query else True
    text = [ 'Por favor, confirma que realmente quieres {}'.format(description) if description is not None else '¿Estás seguro?' ]
    menu = [ [ InlineKeyboardButton('Sí', callback_data = get_callback_data('indirect-action', action_modifiers = { 'delete-message': delete_message, 'data': get_callback_data(data['action'], action_modifiers = data) })) ], [ InlineKeyboardButton('No', callback_data = get_callback_data('indirect-action', action_modifiers = { 'delete-message': delete_message, 'caller': data['action'], 'data': get_callback_data('show-menu', action_modifiers = data) })) ] ]
    await send_menu_message(update, text, menu)

async def _indirect_action(update, context, data):
    if 'delete-message' in data and data['delete-message']:
        await delete_menu_message(update.callback_query.message)
    if 'data' in data:
        caller = data['caller'] if 'caller' in data else None
        data = data['data']
        if 'action' in data:
            if data['action'] == 'show-menu':
                if caller == 'set-alarm-arm-mode':
                    data['action'] = 'alarm-menu'
                elif caller == 'interact-with-a-camera':
                    data['action'] = 'camera-menu'
                elif caller == 'interact-with-a-docker':
                    data['action'] = 'docker-menu'
                elif caller == 'interact-with-the-vpn':
                    data['action'] = 'vpn-menu'
                if data['action'] != 'show-menu' and 'root-menu' in data:
                    await _menu(update, context, data)
            else:
                data['action-confirmed'] = True
                if data['action'] == 'set-alarm-arm-mode':
                    await _set_alarm_arm_mode(update, context, data)
                elif data['action'] == 'interact-with-a-camera':
                    await _interact_with_a_camera(update, context, data)
                elif data['action'] == 'interact-with-a-docker':
                    await _interact_with_a_docker(update, context, data)
                elif data['action'] == 'interact-with-the-vpn':
                    await _interact_with_the_vpn(update, context, data)

async def indirect_action(update, context):
    await _indirect_action(update, context, update.callback_query.data)

def is_indirect_action_request(data):
    return isinstance(data, dict) and 'action' in data and data['action'] == 'indirect-action'

##### Interacción con la alarma

async def _set_alarm_arm_mode(update, context, data):
    callback_query_answer_done = False
    if 'arm-mode' in data and config_block_exists('ALARMO') and is_user_allowed_to_interact_with_the_chat(get_effective_user(update), get_effective_chat(update)) and AlarmoUtils.can_change_state():
        arm_mode = data['arm-mode']
        if arm_mode in ALARMO_ACTIONS:
            command, state = ALARMO_ACTIONS[arm_mode]['command'], ALARMO_ACTIONS[arm_mode]['state']
            if _is_confirmed(config.ALARMO, arm_mode, data):
                message = await update.effective_chat.send_message('Espera mientras tratamos de acceder a la alarma para desconectarla.' if arm_mode == 'disarm' else 'Espera mientras tratamos de acceder a la alarma para configurarla en modo "{}".'.format(_get_alarmo_arm_mode_name(arm_mode)), disable_notification = True)
                success = AlarmoUtils.send_command(command, state)
                await message.delete()
                if success and 'root-menu' in data:
                    await _menu(update, context, { 'action': 'alarm-menu', 'root-menu': data['root-menu'] })
                await callback_query_answer(update)
                callback_query_answer_done = True
            else:
                await callback_query_answer(update)
                callback_query_answer_done = True
                await _confirm(update, 'desconectar la alarma' if arm_mode == 'disarm' else 'configurar la alarma en modo "{}"'.format(_get_alarmo_arm_mode_name(arm_mode)), data)
    if not callback_query_answer_done:
        await callback_query_answer(update)

async def set_alarm_arm_mode(update, context):
    await _set_alarm_arm_mode(update, context, update.callback_query.data)

def is_set_alarm_arm_mode_request(data):
    return isinstance(data, dict) and 'action' in data and data['action'] == 'set-alarm-arm-mode'

##### Interacción con una cámara

async def _interact_with_a_camera(update, context, data):
    callback_query_answer_done = False
    if 'camera-id' in data and 'command' in data and config_block_exists('CAMERAS') and await is_user_allowed_to_exec_administrative_commands(get_effective_user(update)):
        camera_data = config.CAMERAS['devices'][data['camera-id']] if 'devices' in config.CAMERAS and data['camera-id'] in config.CAMERAS['devices'] else None
        if camera_data is not None:
            if 'oems' in config.CAMERAS and 'oem' in camera_data and camera_data['oem'] in config.CAMERAS['oems']:
                if data['command'] == 'restart':
                    if _is_confirmed(config.CAMERAS, data['command'], data):
                        message = await update.effective_chat.send_message('Espera mientras tratamos de acceder a la cámara para reiniciarla.', disable_notification = True)
                        camera_oem = config.CAMERAS['oems'][camera_data['oem']]
                        CameraUtils.restart(camera_data['oem'], camera_data['ip'], camera_oem['user'], camera_oem['password'])
                        await message.delete()
                        await callback_query_answer(update)
                        callback_query_answer_done = True
                    else:
                        await callback_query_answer(update)
                        callback_query_answer_done = True
                        await _confirm(update, 'reiniciar la cámara "{}"'.format(camera_data['name']), data)
    if not callback_query_answer_done:
        await callback_query_answer(update)

async def interact_with_a_camera(update, context):
    await _interact_with_a_camera(update, context, update.callback_query.data)

def is_interact_with_a_camera_request(data):
    return isinstance(data, dict) and 'action' in data and data['action'] == 'interact-with-a-camera';

##### Interacción con una cámara

async def handle_camera_command(update, context):
    await update.message.delete()
    if len(context.args) == 1:
        await _menu(update, context, { 'action': 'camera-menu', 'camera-id': context.args[0], 'root-menu': 'camera-menu' })
    elif len(context.args) == 2:
        await _interact_with_a_camera(update, context, { 'action': 'interact-with-a-camera', 'camera-id': context.args[0], 'command': context.args[1] })
    else:
        await _menu(update, context, { 'action': 'cameras-menu', 'root-menu': 'cameras-menu' })
    
##### Interacción con un docker

async def _interact_with_a_docker(update, context, data):
    callback_query_answer_done = False
    if 'command' in data and 'docker-id' in data and data['command'] in DOCKER_ACTIONS and config_block_exists('DOCKERS') and await is_user_allowed_to_exec_administrative_commands(get_effective_user(update)):
        name = DockerUtils.get_container_name(data['docker-id'])
        if _is_confirmed(config.DOCKERS, data['command'], data):
            message = await update.effective_chat.send_message('Espera mientras tratamos de acceder a "{}" para {}.'.format(name, DOCKER_ACTIONS[data['command']]['action']), disable_notification = True)
            if data['command'] == 'delete':
                DockerUtils.delete_container(data['docker-id'])
                if not DockerUtils.container_exists(data['docker-id']) and 'root-menu' in data:
                    data['action'] = 'dockers-menu'
                    await _menu(update, context, data)
            else:
                is_running = DockerUtils.is_container_running(data['docker-id'])
                if data['command'] == 'start':
                    DockerUtils.start_container(data['docker-id'], config.DOCKERS['host-indirection'] if 'host-indirection' in config.DOCKERS else None)
                elif data['command'] == 'stop':
                    DockerUtils.stop_container(data['docker-id'])
                elif data['command'] == 'restart':
                    DockerUtils.restart_container(data['docker-id'], config.DOCKERS['host-indirection'] if 'host-indirection' in config.DOCKERS else None)
                if DockerUtils.is_container_running(data['docker-id']) != is_running and 'root-menu' in data:
                    data['action'] = 'docker-menu'
                    await _menu(update, context, data)
            await message.delete()
            await callback_query_answer(update)
            callback_query_answer_done = True
        else:
            await callback_query_answer(update)
            callback_query_answer_done = True
            await _confirm(update, '{} el contenedor "{}"'.format(DOCKER_ACTIONS[data['command']]['confirm-action'], name), data)
    if not callback_query_answer_done:
        await callback_query_answer(update)


async def interact_with_a_docker(update, context):
    await _interact_with_a_docker(update, context, update.callback_query.data)

def is_interact_with_a_docker_request(data):
    return isinstance(data, dict) and 'action' in data and data['action'] == 'interact-with-a-docker';

##### Interacción con la VPN

async def _interact_with_the_vpn(update, context, data):
    callback_query_answer_done = False
    if 'command' in data and data['command'] in [ 'start', 'stop' ] and config_block_exists('VPN') and await is_user_allowed_to_exec_administrative_commands(get_effective_user(update)):
        if 'type' in config.VPN:
            if config.VPN['type'] == 'docker' and 'docker' in config.VPN:
                if _is_confirmed(config.VPN, data['command'], data):
                    is_running, will_be_run = DockerUtils.is_container_running(config.VPN['docker']), data['command'] == 'start'
                    message = None
                    if is_running != will_be_run:
                        message = await update.effective_chat.send_message('Espera mientras tratamos de acceder a la VPN para {}.'.format('encenderla' if data['command'] == 'start' else 'apagarla'), disable_notification = True)
                        if data['command'] == 'start':
                            DockerUtils.start_container(config.VPN['docker'], config.DOCKERS['host-indirection'] if config_block_exists('DOCKERS') and 'host-indirection' in config.DOCKERS else None)
                        else:
                            DockerUtils.stop_container(config.VPN['docker'])
                    if DockerUtils.is_container_running(config.VPN['docker']) == will_be_run and not 'root-menu' in data:
                        if message != None:
                            await message.delete()
                        message = await update.effective_chat.send_message('La VPN ya está {}.'.format('encendida' if data['command'] == 'start' else 'apagada'), disable_notification = True)
                        sleep(5)
                    await message.delete()
                    await callback_query_answer(update)
                    if 'root-menu' in data:
                        data['action'] = 'vpn-menu'
                        await _menu(update, context, data)
                    callback_query_answer_done = True
                else:
                    await callback_query_answer(update)
                    callback_query_answer_done = True
                    await _confirm(update, '{} la VPN"'.format('encender' if data['command'] == 'start' else 'apagar'), data)
    if not callback_query_answer_done:
        await callback_query_answer(update)

async def interact_with_the_vpn(update, context):
    await _interact_with_the_vpn(update, context, update.callback_query.data)

def is_interact_with_the_vpn_request(data):
    return isinstance(data, dict) and 'action' in data and data['action'] == 'interact-with-the-vpn';

##### Interacción con una cámara

async def handle_vpn_command(update, context):
    await update.message.delete()
    if len(context.args) == 1 and context.args[0] in [ 'on', 'off' ]:
        await _interact_with_the_vpn(update, context, { 'action': 'interact-with-the-vpn', 'command': 'start' if context.args[0] == 'on' else 'stop' })
    else:
        await _menu(update, context, { 'action': 'vpn-menu', 'root-menu': 'vpn-menu' })

##### Obtener la IP pública del router

async def _whats_my_ip(update, context):
    callback_query_answer_done = False
    if is_user_allowed_to_interact_with_the_chat(get_effective_user(update), get_effective_chat(update)):
        message = await update.effective_chat.send_message('Espera un momento mientras tratamos de obtener la dirección IP pública del router.')
        ip = WhatsMyIp.get()
        await message.edit_text('La dirección IP del router es la "{}"'.format(ip) if ip is not None else 'No se ha podido obtener la dirección IP del router')
        await callback_query_answer(update)
        callback_query_answer_done = True
    if not callback_query_answer_done:
        await callback_query_answer(update)

async def whats_my_ip(update, context):
    await _whats_my_ip(update, context)

def is_whats_my_ip_request(data):
    return isinstance(data, dict) and 'action' in data and data['action'] == 'whats-my-ip'

async def handle_whats_my_ip_command(update, context):
    await update.message.delete()
    await _whats_my_ip(update, context)

##### Obtener el uptime de la máquina

async def _uptime(update, context):
    callback_query_answer_done = False
    if is_user_allowed_to_interact_with_the_chat(get_effective_user(update), get_effective_chat(update)):
        message = await update.effective_chat.send_message('El último reinicio fue el {} a las {} ({})'.format(datetime.fromtimestamp(time() - get_uptime(False)).strftime('%d/%m/%Y'), datetime.fromtimestamp(time() - get_uptime(False)).strftime('%H:%M:%S'), get_uptime(True)))
        await callback_query_answer(update)
        callback_query_answer_done = True
    if not callback_query_answer_done:
        await callback_query_answer(update)

async def uptime(update, context):
    await _uptime(update, context)

def is_uptime_request(data):
    return isinstance(data, dict) and 'action' in data and data['action'] == 'uptime'

async def handle_uptime_command(update, context):
    await update.message.delete()
    await _uptime(update, context)

##### El usuario quiere ocultar el menú

async def exit_menu(update, context):
    await callback_query_answer(update)
    message = update.callback_query.message
    await delete_menu_message(message)

def is_exit_menu_request(data):
    return isinstance(data, dict) and 'action' in data and data['action'] == 'exit';

##### Opción inválida

async def handle_invalid_button(update, context):
    await callback_query_answer(update)
    message = [
        'La acción solicitada no se reconoce.',
        'Si has usado el teclado, comprueba que no hayas cometido algún error de escritura.',
        'En caso que hayas hecho clic en el botón de un menú, te informamos de que los menús dejan de ser válidos al cabo de un tiempo, por lo que te recomendamos que no uses menús antiguos y que hagas clic en el botón "< salir" cuando acabes de utilizar el bot.'
        'Para conocer la lista completa de comandos reconocidos teclea /commands',
    ]
    message = await update.effective_chat.send_message("\n\n".join(message), disable_notification = True)
    sleep(10)
    await message.delete()
    await update.callback_query.message.delete()

##### Main

async def post_init(application):
    commands = []
    if config_block_exists('ALARMO'):
        commands.append(BotCommand('alarm', 'para visualizar las opciones de la alarma.'))
    if config_block_exists('CAMERAS'):
        commands.append(BotCommand('cameras', 'para visualizar las opciones de gestión de cámaras.'))
    commands.append(BotCommand('commands', 'para visualizar la lista de comandos disponibles.'))
    if config_block_exists('DOCKERS'):
        commands.append(BotCommand('dockers', 'para visualizar las opciones de gestión de contenedores.'))
    if config_block_exists('VPN'):
        commands.append(BotCommand('vpn', 'para visualizar las opciones de gestión de la VPN'))
    commands.append(BotCommand('menu', 'para visualizar el menú del bot.'))
    commands.append(BotCommand('uptime', 'para visualizar cuándo se realizó el último reinicio.'))
    commands.append(BotCommand('whatsmyip', 'para visualizar la dirección IP pública del router.'))
    await application.bot.set_my_commands(commands)
    BOT_MESSAGES.clear()

async def post_stop(application): 
    for chat_id in BOT_MESSAGES:
        for message_id in BOT_MESSAGES[chat_id]:
            await application.bot.delete_message(chat_id, message_id)
    
if __name__ == '__main__':
    logging.basicConfig(level = config.LOG_LEVEL)
    MqttAgent.initialize()
    AlarmoUtils.initialize()
    DockerUtils.initialize()
    application = Application.builder().token(config.TELEGRAM['bot-token']).arbitrary_callback_data(True).post_init(post_init).post_stop(post_stop).build()
    application.add_error_handler(error_handler)
    application.add_handler(ChatMemberHandler(greet_chat_members, ChatMemberHandler.CHAT_MEMBER))
    application.add_handler(CommandHandler([ 'menu', 'start' ], menu))
    application.add_handler(CommandHandler([ 'commands', 'help' ], list_commands))
    application.add_handler(CommandHandler('alarm', alarm_menu))
    application.add_handler(CommandHandler('cameras', cameras_menu))
    application.add_handler(CommandHandler('camera', handle_camera_command))
    application.add_handler(CommandHandler('dockers', dockers_menu))
    application.add_handler(CommandHandler('vpn', handle_vpn_command))
    application.add_handler(CommandHandler('whatsmyip', handle_whats_my_ip_command))
    application.add_handler(CommandHandler('uptime', handle_uptime_command))
    application.add_handler(CallbackQueryHandler(menu, pattern = is_menu_request))
    application.add_handler(CallbackQueryHandler(set_alarm_arm_mode, pattern = is_set_alarm_arm_mode_request))
    application.add_handler(CallbackQueryHandler(interact_with_a_camera, pattern = is_interact_with_a_camera_request))
    application.add_handler(CallbackQueryHandler(interact_with_a_docker, pattern = is_interact_with_a_docker_request))
    application.add_handler(CallbackQueryHandler(interact_with_the_vpn, pattern = is_interact_with_the_vpn_request))
    application.add_handler(CallbackQueryHandler(indirect_action, pattern = is_indirect_action_request))
    application.add_handler(CallbackQueryHandler(whats_my_ip, pattern = is_whats_my_ip_request))
    application.add_handler(CallbackQueryHandler(uptime, pattern = is_uptime_request))
    application.add_handler(CallbackQueryHandler(exit_menu, pattern = is_exit_menu_request))
    application.add_handler(CallbackQueryHandler(handle_invalid_button, pattern = InvalidCallbackData))
    application.run_polling(allowed_updates = Update.ALL_TYPES)
