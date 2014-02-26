# -*- coding: utf-8 -*-
'''
KTN-project 2013 / 2014
Very simple server implementation that should serve as a basis
for implementing the chat server
'''
import SocketServer
from Message import *  # All Message types
import datetime        # Get current date (for displaying when a chat message was sent)
import time            # Get current time (for displaying when a chat message was sent)
import json            # decode network data
import re              # For validation of username

'''
The RequestHandler class for our server.

It is instantiated once per connection to the server, and must
override the handle() method to implement communication to the
client.
'''


class Controller:
    def __init__(self):
        self.messages = []
        self.users = []
        self.client_handlers = []

    def register_client_handler(self, client_handler):
        self.client_handlers.append(client_handler)

    def unregister_client_handler(self, client_handler):
        if client_handler in self.client_handlers:
            self.client_handlers.remove(client_handler)

    def broadcast(self, message, __except):
        chatMessageResponse = ChatResponseMessage()
        chatMessageResponse.set_success(message)
        json_data = chatMessageResponse.get_JSON()

        for client_handler in self.client_handlers:
            if client_handler != __except:
                client_handler.send(json_data)

    # Returns:
    # True if username is taken
    # False if available
    def get_user_logged_in(self, username):
        return self.users.count(username) == 1

    def set_user_logged_in(self, username):
        if not self.get_user_logged_in(username):
            self.users.append(username)
            return True
        return False

    def get_all_online(self):
        return self.users

    def get_all_messages(self):
        return self.messages

    def valid_username(self, username):
        match_obj = re.search('[A-zæøåÆØÅ_0-9]+', username)
        return match_obj is not None and match_obj.group(0) == username

    def notify_message(self, message, client_handler):
        self.messages.append(message)
        self.broadcast(message, client_handler)

    def set_user_logged_out(self, username):
        if username in self.users:
            self.users.remove(username)



class ClientHandler(SocketServer.BaseRequestHandler):
    controller = Controller()

    def connection_to_username(self):
        self.connection = self.request

    def send(self, message):
        try:
            self.connection.sendall(message)
        except:
            controller.unregister_client_handler(self)
            controller.set_user_logged_out(self.username)


    def handle(self):
        # Initialize username to None so we know the user isn't logged in
        self.username = None

        # Get a reference to the socket object
        self.connection = self.request

        # Get the remote ip address of the socket
        self.ip = self.client_address[0]

        # Get the remote port number of the socket
        self.port = self.client_address[1]

        print 'Client connected @' + self.ip + ':' + str(self.port)


        while True:
            # Wait for data from the client
            try:
                json_data = self.connection.recv(1024).strip()
            except:
                break

            # Check if the data exists (if it doesn't it means the client disconnected)
            if json_data:
                print "Message received from " + str(self.username) + ": " + str(json_data)

                # responseMessage will be the message to return
                responseMessage = None
                data = json.loads(json_data)

                if "request" in data:
                    request = data["request"]

                    if request == "login":

                        if "username" in data:
                            self.username = data["username"]
                            responseMessage = LoginResponseMessage()

                            # Check for invalid username
                            if not controller.valid_username(self.username):
                                responseMessage.set_invalid_username(self.username)
                                self.username = None

                            # See if we can log in (fails if already used)
                            elif controller.set_user_logged_in(self.username):
                                responseMessage.set_success(self.username, controller.get_all_messages())
                                print "Client " + self.username + " logged in!"

                                # Register this object so we get broadcast messages
                                controller.register_client_handler(self)

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
                            if not controller.get_user_logged_in(self.username):
                                responseMessage.set_not_logged_in()

                            # Everything is fine, send message back to sender and then broadcast to everyone else
                            else:
                                #responseMessage.set_success(message)
                                responseMessage = None

                                # This also broadcasts to everyone except the sender
                                #datetime.date.today().strftime("%d/%m/%Y ")
                                now_string = time.strftime("%H:%M:%S")
                                controller.notify_message(self.username + " " + now_string + ": " + message, self)

                    elif request == "listUsers":
                        responseMessage = ListUsersResponseMessage()
                        responseMessage.set_users(controller.get_all_online())


                    elif request == "logout":
                        responseMessage = LogoutResponseMessage()

                        # All is fine, log user out and unregister ourselves so we don't receive broadcasts.
                        if controller.get_user_logged_in(self.username):
                            responseMessage.set_success(self.username)
                            controller.set_user_logged_out(self.username)
                            controller.unregister_client_handler(self)
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

                if responseMessage is not None:
                    json_data = responseMessage.get_JSON()
                    self.send(json_data)

            else:
                break

        print 'Client ' + str(self.username) + ' disconnected!'
        controller.set_user_logged_out(self.username)
        controller.unregister_client_handler(self)
        self.connection.close()


'''
This will make all Request handlers being called in its own thread.
Very important, otherwise only one client will be served at a time
'''


class ThreadedTCPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    pass

if __name__ == "__main__":
    HOST = ''
    PORT = 9998

    controller = Controller()

    ClientHandler.persist = controller

    # Create the server, binding to localhost on port 9999
    server = ThreadedTCPServer((HOST, PORT), ClientHandler)

    # Activate the server; this will keep running until you
    # interrupt the program with Ctrl-C
    try:
        server.serve_forever()
    except KeyboardInterrupt, e:
        server.server_close()
