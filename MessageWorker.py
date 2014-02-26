'''
KTN-project 2013 / 2014
Python daemon thread class for listening for events on
a socket and notifying a listener of new messages or
if the connection breaks.

A python thread object is started by calling the start()
method on the class. in order to make the thread do any
useful work, you have to override the run() method from
the Thread superclass. NB! DO NOT call the run() method
directly, this will cause the thread to block and suspend the
entire calling process' stack until the run() is finished.
it is the start() method that is responsible for actually
executing the run() method in a new thread.
'''
from threading import Thread
import json


class MessageWorker(Thread):
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
