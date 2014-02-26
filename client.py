'''
KTN-project 2013 / 2014
'''
import socket
from Message import *
import threading


class MessageWorker(threading.Thread):
    def __init__(self, connection, client):
        super(MessageWorker, self).__init__(name="Listener")
        self.connection = connection
        self.client = client

    def run(self):
        run = True

        while run:
            json_data = self.connection.recv(1024).strip()

            # Decode and send data to client
            if json_data:
                data = json.loads(json_data)
                self.send_data(data)

            # Server closed connection
            else:
                run = False

        self.client.connection_closed()

    def send_data(self, data):
        self.client.message_received(data)


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
