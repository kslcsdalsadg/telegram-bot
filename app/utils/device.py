import os

class DeviceUtils():
    @staticmethod
    def is_online(ip_address):
        return os.system("ping -c 1 " + ip_address) == 0 

