# -*- coding: utf-8 -*-
import sys             # Exit if not Python 3
if sys.version_info[0] != 3:
    print("You need to run this with Python 3!")
    sys.exit(1)

import socketserver
from Message import *  # All Message types
import time            # Get current time (for displaying when a chat message was sent)
import json            # decode network data
import re              # For validation of username
import sqlite3         # Database connection
import threading


# The RequestHandler class for our server.
#
# It is instantiated once per connection to the server, and must
# override the handle() method to implement communication to the
# client.


class Controller:
    def __init__(self):
        self.messages = []
        self.users = []
        self.client_handlers = []

        self.lock = threading.Lock()

        # Connect to database called "chat.db" - create it if it doesn't exist
        # check_same_thread=False enables access to the object from different threads
        # TODO: Make it use a producer / consumer pattern instead?
        self.db_con = sqlite3.connect("chat.db", check_same_thread=False)

        # We're using this to query the database
        self.db_cursor = self.db_con.cursor()

        # Initialize db: Create the table if it doesn't exist
        # Docs: http://sqlite.org/lang_createtable.html
        # TODO: Extract this into its own function?
        query = "CREATE TABLE IF NOT EXISTS chat_messages"
        query += " (id INTEGER PRIMARY KEY AUTOINCREMENT, message TEXT, sender TEXT, timestamp INT);"
        self.db_cursor.execute(query)  # Run the query
        self.db_con.commit()           # Save changes from memory to disk

        # Load chat messages from database
        self.load_chat_messages()

    def load_chat_messages(self):
        # Fetch all messages ordered by oldest first
        # TODO: Fetching WILL get slower as the table grows
        query = "SELECT * FROM chat_messages ORDER BY timestamp ASC;"

        # Row is a tuple: (id, message, sender, timestamp)
        for row in self.db_cursor.execute(query):
            self.messages.append(row)

    def register_client_handler(self, client_handler):
        self.lock.acquire()
        self.client_handlers.append(client_handler)
        self.lock.release()

    def unregister_client_handler(self, client_handler):
        self.lock.acquire()
        if client_handler in self.client_handlers:
            self.client_handlers.remove(client_handler)
        self.lock.release()

    def broadcast(self, message):
        chatMessageResponse = ChatResponseMessage()
        chatMessageResponse.set_success(message)
        json_data = chatMessageResponse.get_JSON()

        for client_handler in self.client_handlers:
            client_handler.send(json_data)

    # Returns:
    # True if username is taken
    # False if available
    def get_user_logged_in(self, username):
        self.lock.acquire()
        res = self.users.count(username) == 1
        self.lock.release()

        return res

    def set_user_logged_in(self, username):
        if not self.get_user_logged_in(username):
            self.lock.acquire()
            self.users.append(username)
            self.lock.release()
            return True
        return False

    def get_all_online(self):
        self.lock.acquire()
        users = self.users
        self.lock.release()

        return users

    def get_all_messages(self):
        self.lock.acquire()
        res = self.messages
        self.lock.release()

        return res

    def valid_username(self, username):
        match_obj = re.search(u'[A-zæøåÆØÅ_0-9]+', username)
        return match_obj is not None and match_obj.group(0) == username

    # sender is username of sender (for use in database)
    def notify_message(self, message, sender):
        query = "INSERT INTO chat_messages (message, sender, timestamp) VALUES (?, ?, ?)"
        now_as_int = int(time.time())
        self.db_cursor.execute(query, (message, sender, now_as_int))
        self.db_con.commit()  # Save to disk

        message_id = self.db_cursor.lastrowid
        message_row = (message_id, message, sender, now_as_int)

        self.lock.acquire()
        self.messages.append(message_row)
        self.broadcast(message_row)
        self.lock.release()

    def set_user_logged_out(self, username):
        self.lock.acquire()
        if username in self.users:
            self.users.remove(username)
        self.lock.release()


class ClientHandler(socketserver.BaseRequestHandler):
    controller = Controller()

    def __init__(self, request, client_address, server):
        self.recv_buffer = ""

        # This IMMEDIATELY calls the handle() function
        super().__init__(request, client_address, server)


    def connection_to_username(self):
        self.connection = self.request

    def send(self, message):
        message_as_bytes = bytes(message, "UTF-8")
        try:
            self.connection.sendall(message_as_bytes)
        except:
            controller.unregister_client_handler(self)
            controller.set_user_logged_out(self.username)

    # Receive data until we have one or more COMPLETE JSON objects to deliver
    # Returns: Exactly *ONE* JSON object
    # or False if connection was closed
    def receive_message(self):
        num_brackets = 0  # "Net worth" of brackets, that is: Number of { minus number of }
        buffer_pos = 0    # How far in the buffer we've searched for an object
        escape_char = False
        inside_quotes = False

        # Essentially: while we haven't found a complete object
        while True:
            # Look for object
            # NOTE: We're doing this before we receive for a reason!
            # This is because we might have received more than one object a previous iteration,
            # and we want to serve those at once
            # If we didn't do this we would have to WAIT for self.connection.recv() to return, meaning that we
            # actually have to receive more data to provide our server with data we already have
            for i in range(buffer_pos, len(self.recv_buffer)):
                buffer_pos = i+1
                if escape_char:
                    escape_char = False
                    continue

                if not inside_quotes:
                    if self.recv_buffer[i] == '{':
                        num_brackets += 1
                    elif self.recv_buffer[i] == '}':
                        num_brackets -= 1

                # The next character doesn't mean what it usually means
                if self.recv_buffer[i] == '\\':
                    escape_char = True

                if self.recv_buffer[i] == '"':
                    inside_quotes = not inside_quotes

                if num_brackets == 0:
                    # Set object_json equal to the first i chars of self.recv_buffer
                    object_json = self.recv_buffer[:i+1]
                    self.recv_buffer = self.recv_buffer[i+1:]

                    return object_json

            # We don't have an object to serve; wait for more data
            received_bytes = self.connection.recv(1024)

            # Connection was closed
            if len(received_bytes) == 0:
                return False

            received_as_string = received_bytes.decode("utf-8")  # Decode received bytes as utf-8
            #print("Received: " + received_as_string)
            self.recv_buffer += received_as_string

    # Socket is closed when we return from this function
    def handle(self):
        # Initialize username to None so we know the user isn't logged in
        self.username = None

        # Get a reference to the socket object
        self.connection = self.request

        # Get the remote ip address of the socket
        self.ip = self.client_address[0]

        # Get the remote port number of the socket
        self.port = self.client_address[1]

        print('Client connected @' + self.ip + ':' + str(self.port))

        while True:
            # Blocks until we have a complete JSON object
            json_data = self.receive_message()

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
                            if not controller.valid_username(self.username):
                                responseMessage.set_invalid_username(self.username)
                                self.username = None

                            # See if we can log in (fails if already used)
                            elif controller.set_user_logged_in(self.username):
                                responseMessage.set_success(self.username, controller.get_all_messages())
                                print("Client " + self.username + " logged in!")

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
                                controller.notify_message(message, self.username)

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

                # Respond with responseMessage (if a response is required by the protocol)
                if responseMessage is not None:
                    json_data = responseMessage.get_JSON()
                    self.send(json_data)

            # Connection was closed
            else:
                break

        print('Client ' + str(self.username) + ' disconnected!')
        controller.set_user_logged_out(self.username)
        controller.unregister_client_handler(self)
        self.connection.close()


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass

if __name__ == "__main__":
    HOST = ''
    #HOST = 'localhost'
    PORT = 9998

    controller = Controller()

    ClientHandler.persist = controller

    # Create the server, binding to localhost on port 9999
    server = ThreadedTCPServer((HOST, PORT), ClientHandler)
    server.daemon_threads = True

    # Activate the server; this will keep running until you
    # interrupt the program with Ctrl-C
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
