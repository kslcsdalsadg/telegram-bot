import requests

class WhatsMyIp():
    URL = 'https://api.ipify.org/?format=json'

    @staticmethod
    def get():
        result = requests.get(WhatsMyIp.URL)
        return result.json()['ip'] if result.status_code == 200 else None



