import requests

class WhatsMyIp():
    URL = 'https://ipv4.icanhazip.com'

    @staticmethod
    def get():
        result = requests.get(WhatsMyIp.URL)
        return result.content.decode('utf-8').strip() if result.status_code == 200 else None



