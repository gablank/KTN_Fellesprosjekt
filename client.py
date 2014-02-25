'''
KTN-project 2013 / 2014
'''
import socket
from Message import *


class Client(object):
    def __init__(self, host, port):
        self.connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.connection.connect((host, port))

    def start(self):
        while not self.login():
            continue

    def message_received(self, message, connection):
        pass

    def connection_closed(self, connection):
        pass

    def login(self):
        self.username = raw_input("Select username: ")
        loginRequestMessage = LoginRequestMessage()
        loginRequestMessage.set_login_info(self.username)
        network_data = loginRequestMessage.get_JSON()
        self.send(network_data)
        print self.connection.recv(1024).strip()
        self.connection.close()

    def send(self, data):
        self.connection.sendall(data)

    def force_disconnect(self):
        pass


if __name__ == "__main__":
    client = Client('localhost', 9999)
    client.login()
