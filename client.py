'''
KTN-project 2013 / 2014
'''
import socket
from Message import *
from MessageWorker import MessageWorker


class Client(object):
    def __init__(self, host, port):
        self.connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.connection.connect((host, port))

        # Start the message worker (which listens on the connection and notifies us if it has received a message)
        self.message_worker = MessageWorker(self.connection, self)

    def start(self):
        pass

    # Message is already decoded from JSON
    def message_received(self, message):
        pass

    # Server closed connection
    def connection_closed(self):
        self.message_worker.join()  # Wait for listener to exit

    def login(self):
        pass

    def send(self, data):
        self.connection.sendall(data)

    def force_disconnect(self):
        self.connection.close()

    def process_data(self, data):
        pass

    # Output this to console
    def output(self, line):
        print line

    # Get input
    def input(self, prompt):
        return raw_input(prompt)


if __name__ == "__main__":
    client = Client('localhost', 9998)
    client.login()
