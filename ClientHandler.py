# -*- coding: utf-8 -*-
import sys  # Exit if not Python 3
if sys.version_info[0] != 3:
    print("You need to run this with Python 3!")
    sys.exit(1)

import socket
import json       # decode network data
from BufferedMessageListener import BufferedMessageListener
from Message import *
import threading


class ClientHandler(threading.Thread):
    def __init__(self, request, client_address, server):
        # Call init of Thread
        threading.Thread.__init__(self)

        # Reference to server
        self.server = server
        # Get a reference to the socket object
        self.connection = request
        # Initialize username to None so we know the user isn't logged in
        self.username = None
        # Returns exactly one JSON object (as utf-8 encoded string, so it has to be decoded)
        self.buffered_receiver = BufferedMessageListener(self.connection)
        # Get the remote ip address of the socket
        self.ip = client_address[0]
        # Get the remote port number of the socket
        self.port = client_address[1]

        self.should_run = True
        self.shutting_down = False

    def send(self, message):
        message_as_bytes = bytes(message, "UTF-8")
        try:
            self.connection.sendall(message_as_bytes)
        except OSError:
            self.shutdown()

    def whoami(self):
        if self.username is None:
            return self.ip + ":" + str(self.port)
        else:
            return self.username

    def run(self):
        print('Client connected @' + self.ip + ':' + str(self.port))

        while self.should_run:
            # Blocks until we have a complete JSON object
            json_data = self.buffered_receiver.receive_message()

            # Check if the data exists (if it doesn't it means the client disconnected)
            if not json_data:
                #Connection was closed
                break

            print("Message received from " + self.whoami() + ": " + str(json_data))

            # responseMessage will be the message to return
            responseMessage = None
            try:
                data = json.loads(json_data)
            except ValueError:
                print("Cannot decode JSON: " + json_data)
                continue

            if "request" in data:
                request = data["request"]

                if request == "login":

                    if "username" in data:
                        new_username = data["username"]

                        responseMessage = LoginResponseMessage()

                        # Check for invalid username
                        if not self.server.valid_username(new_username):
                            responseMessage.set_invalid_username(new_username)

                        # Username taken
                        elif not self.server.available_username(new_username):
                            responseMessage.set_taken_username(new_username)

                        else:
                            self.username = new_username
                            responseMessage.set_success(self.username, self.server.get_all_messages())
                            print("Client " + self.whoami() + " logged in!")
                            self.server.notify_login(self.username)

                    else:
                        responseMessage = ProtocolErrorMessage()
                        responseMessage.set_error_message("Required field 'username' not present!")

                elif request == "message":

                    if "message" in data:
                        message = data["message"]

                        responseMessage = ChatResponseMessage()

                        # Not logged in, don't broadcast
                        if self.username is None:
                            responseMessage.set_not_logged_in()

                        # Everything is fine, send message back to sender and then broadcast to everyone else
                        else:
                            responseMessage = None

                            # This also broadcasts to everyone
                            self.server.add_message(message, self.username)

                elif request == "listUsers":
                    responseMessage = ListUsersResponseMessage()
                    responseMessage.set_users(self.server.get_all_online())

                elif request == "logout":
                    responseMessage = LogoutResponseMessage()

                    # All is fine, log user out
                    if self.username is not None:
                        responseMessage.set_success(self.username)
                        self.server.notify_logout(self.username)
                        self.username = None

                    # Can't log out: you need to log in first! :D
                    else:
                        responseMessage.set_not_logged_in(self.username)

                else:
                    responseMessage = ProtocolErrorMessage()
                    responseMessage.set_error_message("Request field should be one of 'login', 'message' and 'logout'!")

            else:
                responseMessage = ProtocolErrorMessage()
                responseMessage.set_error_message("Required field 'username' not present!")

            # Respond with responseMessage (if a response is required by the protocol)
            if responseMessage is not None:
                json_data = responseMessage.get_JSON()
                self.send(json_data)

        self.shutdown()

    def shutdown(self):
        if not self.shutting_down:
            self.shutting_down = True
            print('Client ' + self.whoami() + ' disconnected!')

            if self.username is not None:
                self.server.notify_logout(self.username)

            self.should_run = False
            self.connection.shutdown(socket.SHUT_RDWR)
            self.connection.close()