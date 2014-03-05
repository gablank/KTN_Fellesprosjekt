# -*- coding: utf-8 -*-
import sys  # Exit if not Python 3
if sys.version_info[0] != 3:
    print("You need to run this with Python 3!")
    sys.exit(1)

import socketserver
import json       # decode network data
from BufferedMessageListener import BufferedMessageListener
from Message import *


class ClientHandler(socketserver.BaseRequestHandler):
    def __init__(self, request, client_address, server):
        self.recv_buffer = ""

        # Initialize username to None so we know the user isn't logged in
        self.username = None

        # Initialized in handle()
        self.buffered_receiver = None

        # This IMMEDIATELY calls the handle() function
        super().__init__(request, client_address, server)

    def send(self, message):
        message_as_bytes = bytes(message, "UTF-8")
        try:
            self.connection.sendall(message_as_bytes)
        except OSError:
            self.server.unregister_client_handler(self)
            self.server.set_user_logged_out(self.username)

    # Socket is closed when we return from this function
    def handle(self):
        # Get a reference to the socket object
        self.connection = self.request

        self.buffered_receiver = BufferedMessageListener(self.connection)

        # Get the remote ip address of the socket
        self.ip = self.client_address[0]

        # Get the remote port number of the socket
        self.port = self.client_address[1]

        print('Client connected @' + self.ip + ':' + str(self.port))

        while True:
            # Blocks until we have a complete JSON object
            json_data = self.buffered_receiver.receive_message()

            # Check if the data exists (if it doesn't it means the client disconnected)
            if json_data:
                print("Message received from " + str(self.username) + ": " + str(json_data))

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
                            self.username = data["username"]

                            responseMessage = LoginResponseMessage()

                            # Check for invalid username
                            if not self.server.valid_username(self.username):
                                responseMessage.set_invalid_username(self.username)
                                self.username = None

                            # See if we can log in (fails if already used)
                            elif self.server.set_user_logged_in(self.username):
                                responseMessage.set_success(self.username, self.server.get_all_messages())
                                print("Client " + self.username + " logged in!")

                                # Register this object so we get broadcast messages
                                self.server.register_client_handler(self)

                            # Username taken
                            else:
                                responseMessage.set_taken_username(self.username)
                                self.username = None

                        else:
                            responseMessage = ProtocolErrorMessage()
                            responseMessage.set_error_message("Required field 'username' not present!")

                    elif request == "message":

                        if "message" in data:
                            message = data["message"]

                            responseMessage = ChatResponseMessage()

                            # Not logged in, don't broadcast
                            if not self.server.get_user_logged_in(self.username):
                                responseMessage.set_not_logged_in()

                            # Everything is fine, send message back to sender and then broadcast to everyone else
                            else:
                                # responseMessage.set_success(message)
                                responseMessage = None

                                # This also broadcasts to everyone except the sender
                                self.server.notify_message(message, self.username)

                    elif request == "listUsers":
                        responseMessage = ListUsersResponseMessage()
                        responseMessage.set_users(self.server.get_all_online())

                    elif request == "logout":
                        responseMessage = LogoutResponseMessage()

                        # All is fine, log user out and unregister ourselves so we don't receive broadcasts.
                        if self.server.get_user_logged_in(self.username):
                            responseMessage.set_success(self.username)
                            self.server.set_user_logged_out(self.username)
                            self.server.unregister_client_handler(self)
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

            # Connection was closed
            else:
                break

        print('Client ' + str(self.username) + ' disconnected!')
        self.server.set_user_logged_out(self.username)
        self.server.unregister_client_handler(self)
        self.connection.close()

    def shutdown(self):
        self.connection.close()