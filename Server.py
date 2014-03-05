# -*- coding: utf-8 -*-
import sys  # Exit if not Python 3
if sys.version_info[0] != 3:
    print("You need to run this with Python 3!")
    sys.exit(1)

import socketserver
import threading
import time       # Get current time (for displaying when a chat message was sent)
import re         # For validation of username
import sqlite3    # Database connection
from Message import *
from ClientHandler import ClientHandler


class ThreadedTCPServer(socketserver.TCPServer):
    def __init__(self, addr, clientHandler):
        socketserver.TCPServer.__init__(self, addr, clientHandler)

        self.messages = []
        self.users = []
        self.client_handlers = []

        self.reserved_usernames = ["SERVER"]

        # http://effbot.org/zone/thread-synchronization.htm
        self.lock = threading.RLock()

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
        self.db_con.commit()  # Save changes from memory to disk

        # Load chat messages from database
        self.load_chat_messages()

    def finish_request(self, request, client_address):
        # RequestHandlerClass is ClientHandler
        client_handler = self.RequestHandlerClass(request, client_address, self)
        client_handler.start()
        self.client_handlers.append(client_handler)

    def load_chat_messages(self):
        # Fetch all messages ordered by oldest first
        # TODO: Fetching WILL get slower as the table grows
        query = "SELECT * FROM (SELECT * FROM chat_messages ORDER BY timestamp DESC LIMIT 100) ORDER BY timestamp ASC;"

        # Row is a tuple: (id, message, sender, timestamp)
        for row in self.db_cursor.execute(query):
            self.messages.append(row)

    def broadcast(self, message):
        self.lock.acquire()
        chatMessageResponse = ChatResponseMessage()
        chatMessageResponse.set_success(message)
        json_data = chatMessageResponse.get_JSON()

        for client_handler in self.client_handlers:
            client_handler.send(json_data)
        self.lock.release()

    # Returns:
    # True if username is taken
    # False if available
    def get_user_logged_in(self, username):
        self.lock.acquire()
        res = self.users.count(username) == 1
        self.lock.release()

        return res

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

    # Check if a username is taken already
    def available_username(self, username):
        self.lock.acquire()
        available = True
        for client_handler in self.client_handlers:
            if client_handler.username == username:
                available = False
                break
        self.lock.release()
        return available

    def valid_username(self, username):
        match_obj = re.search(u'[A-zæøåÆØÅ_0-9]+', username)
        return match_obj is not None \
            and match_obj.group(0) == username \
            and username not in self.reserved_usernames \
            and len(username) <= 20

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

    def notify_login(self, username):
        self.notify_message(username + " has logged in!", "SERVER")

    def notify_logout(self, username):
        self.notify_message(username + " has logged out!", "SERVER")

    # Called by ClientHandler
    # Closes the ClientHandler's socket and joins() the thread
    # Removes it from list of ClientHandlers
    def connection_closed(self, client_handler):
        self.lock.acquire()
        self.shutdown_client_handler(client_handler)
        self.lock.release()

    def shutdown_client_handler(self, client_handler):
        client_handler.shutdown()
        self.client_handlers.remove(client_handler)

    def shutdown(self):
        self.lock.acquire()
        for client_handler in self.client_handlers:
            self.shutdown_client_handler(client_handler)
        self.lock.release()



if __name__ == "__main__":
    HOST = ''
    # HOST = 'localhost'
    PORT = 9998

    # Create the server, binding to localhost on port 9999
    server = ThreadedTCPServer((HOST, PORT), ClientHandler)
    server.daemon_threads = True

    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.start()

    while True:
        print("Waiting for input")
        _input = sys.stdin.readline().strip()

        print("Got input: " + _input)

        if _input == "stop":
            print("Shutting down server")
            server.shutdown()
            server.server_close()
            break

    server_thread.join()
