'''
KTN-project 2013 / 2014
Very simple server implementation that should serve as a basis
for implementing the chat server
'''
import SocketServer
from Message import *
import json
import re

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
                client_handler.connection.sendall(json_data)

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
        match_obj = re.search('[A-z_0-9]{1,}', username)
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

    def handle(self):
        username = None
        state = "new"

        # Get a reference to the socket object
        self.connection = self.request
        # Get the remote ip address of the socket
        self.ip = self.client_address[0]
        # Get the remote port number of the socket
        self.port = self.client_address[1]
        print 'Client connected @' + self.ip + ':' + str(self.port)


        while True:
            # Wait for data from the client
            json_data = self.connection.recv(1024).strip()
            # Check if the data exists
            # (recv could have returned due to a disconnect)
            if json_data:
                print controller.get_all_online()
                responseMessage = None
                data = json.loads(json_data)

                if "request" in data:
                    request = data["request"]

                    if request == "login":

                        if "username" in data:
                            username = data["username"]
                            responseMessage = LoginResponseMessage()

                            # Check for invalid username
                            if not controller.valid_username(username):
                                responseMessage.set_invalid_username(username)
                                username = None

                            # See if we can log in (fails if already used)
                            elif controller.set_user_logged_in(username):
                                responseMessage.set_success(username, controller.get_all_messages())
                                print "Client " + username + " logged in!"

                                # Register this object so we get broadcast messages
                                controller.register_client_handler(self)

                            # Username taken
                            else:
                                responseMessage.set_taken_username(username)
                                username = None
                        else:
                            print "Required field 'username' not present!"
                            self.connection.sendall("Required field 'username' not present!")
                            break


                    elif request == "message":

                        if "message" in data:
                            message = data["message"]

                            responseMessage = ChatResponseMessage()

                            # Not logged in, don't broadcast
                            if not controller.get_user_logged_in(username):
                                responseMessage.set_not_logged_in()

                            # Everything is fine, send message back to sender and then broadcast to everyone else
                            else:
                                responseMessage.set_success(message)

                                # This also broadcasts to everyone except the sender
                                controller.notify_message(username + " " + time.time() + ": " + message, self)

                    elif request == "logout":
                        responseMessage = LogoutResponseMessage()

                        # All is fine, log user out and unregister ourselves so we don't receive broadcasts.
                        if controller.get_user_logged_in(username):
                            responseMessage.set_success(username)
                            controller.set_user_logged_out(username)
                            controller.unregister_client_handler(self)
                            username = None

                        # Can't log out: you need to log in first! :D
                        else:
                            responseMessage.set_not_logged_in(username)

                    else:
                        print "Request field should be one of 'login', 'message' and 'logout'!"
                        self.connection.sendall("Request field should be one of 'login', 'message' and 'logout'!")
                        break
                else:
                    print "Required field 'username' not present!"
                    self.connection.sendall("Required field 'username' not present!")
                    break

                if responseMessage is not None:
                    json_data = responseMessage.get_JSON()
                    self.connection.sendall(json_data)

            else:
                print 'Client ' + str(username) + ' disconnected!'
                controller.set_user_logged_out(username)
                controller.unregister_client_handler(self)
                self.connection.close()
                break


'''
This will make all Request handlers being called in its own thread.
Very important, otherwise only one client will be served at a time
'''


class ThreadedTCPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    pass

if __name__ == "__main__":
    HOST = 'localhost'
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
