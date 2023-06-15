from pytapo import Tapo
from time import sleep

import os

class CameraUtils():
    CONFIG = { 'max-wait-time-for-tapo-camera-reboot': 60 }

    @staticmethod
    def _is_tapo_online(ip_address):
        return os.system("ping -c 1 " + ip_address) == 0 
        
    @staticmethod
    def _restart_tapo(ip_address, username, password):
        tapo = Tapo(ip_address, username, password)
        tapo.reboot()
        sleep(15)
        for i in range(CameraUtils.CONFIG['max-wait-time-for-tapo-camera-reboot']):
            if CameraUtils._is_tapo_online(ip_address): 
                break 
            sleep(i)
              
    @staticmethod
    def is_online(camera_vendor, ip_address):
        if camera_vendor == 'tapo':
            return CameraUtils._is_tapo_online(ip_address)
        return False
              
    @staticmethod
    def restart(camera_vendor, ip_address, username, password):
        if CameraUtils.is_online(camera_vendor, ip_address):
            if camera_vendor == 'tapo':
                CameraUtils._restart_tapo(ip_address, username, password)
        
