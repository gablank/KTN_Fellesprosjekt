# -*- coding: utf-8 -*-
import sys
if sys.version_info[0] != 3:
    print("You need to run this with Python 3!")
    sys.exit(1)

from threading import Thread
import json


class MessageWorker(Thread):
    def __init__(self, connection, client):
        super(MessageWorker, self).__init__(name="Listener")
        self.connection = connection
        self.client = client
        self.daemon = True

    def run(self):
        run = True

        while run:
            json_data = self.connection.recv(1500).strip()

            # Decode and send data to client
            if json_data:
                # json_data = str(json_data)
                json_data = json_data.decode("UTF-8")
                #print("Received data from server: " + json_data)

                data = json.loads(json_data)
                self.send_data(data)

            # Server closed connection
            else:
                run = False

        self.client.connection_closed()

    def send_data(self, data):
        self.client.message_received(data)
