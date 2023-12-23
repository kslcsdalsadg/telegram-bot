from utils.device import DeviceUtils

from pytapo import Tapo
from time import sleep

import os

class CameraUtils():
    CONFIG = { 'max-wait-time-for-tapo-camera-reboot': 60 }
       
    @staticmethod
    def _restart_tapo(ip_address, username, password):
        tapo = Tapo(ip_address, username, password)
        tapo.reboot()
        sleep(15)
        for i in range(CameraUtils.CONFIG['max-wait-time-for-tapo-camera-reboot']):
            if DeviceUtils.is_online(ip_address): 
                break 
            sleep(i)
                            
    @staticmethod
    def restart(camera_vendor, ip_address, username, password):
        if DeviceUtils.is_online(ip_address):
            if camera_vendor == 'tapo':
                CameraUtils._restart_tapo(ip_address, username, password)
        
