import netifaces
from Chamber import Chamber

class NetworkClient:
    def __init__(self):
        self.ip = netifaces.ifaddresses('eth0')[netifaces.AF_INET][0]['addr']

        self.chamber = Chamber()
