from utils.device import DeviceUtils

from time import sleep

import os

class WakeOnLan():
    CONFIG = { 'max-wait-time-for-maquine-boot': 60 }

    @staticmethod
    def start(mac_address, ip_address = None):
        if not DeviceUtils.is_online(ip_address):
            os.system("wakeonlan " + mac_address)
            sleep(15)
            if ip_address is not None:
                for i in range(WakeOnLanUtils.CONFIG['max-wait-time-for-maquine-boot']):
                    if DeviceUtils.is_online(ip_address):
                        break
                    sleep(i)
