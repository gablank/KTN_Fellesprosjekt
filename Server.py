# -*- coding: utf-8 -*-
import sys  # Exit if not Python 3
if sys.version_info[0] != 3:
    print("You need to run this with Python 3!")
    sys.exit(1)

import socketserver
import socket
import threading
import time       # Get current time (for displaying when a chat message was sent)
import re         # For validation of username
import sqlite3    # Database connection
import queue
from Message import *
from ClientHandler import ClientHandler


class ThreadedTCPServer(socketserver.TCPServer):
    def __init__(self, addr, clientHandler):
        self.allow_reuse_address = True
        socketserver.TCPServer.__init__(self, addr, clientHandler)

        self.messages = []
        self.users = []
        self.client_handlers = []

        self.reserved_usernames = ["SERVER"]

        # FIFO queue
        # Queue already implements all necessary thread locking mechanisms
        self.queue = queue.Queue()

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

    def queue_worker(self):
        self.notify_message("Server has started")
        while True:
            task = self.queue.get()

            if task[0] == "message":
                message = task[1]
                sender = task[2]
                self.notify_message(message, sender)

            elif task[0] == "shutdown":
                print("Shutting down server...")
                self.notify_message("Server is shutting down")
                # Shut down all client handler threads
                self.lock.acquire()
                for client_handler in self.client_handlers:
                    self.client_handlers.remove(client_handler)
                    self.shutdown_client_handler(client_handler)
                    client_handler.join()
                self.lock.release()
                self.shutdown()

                self.socket.shutdown(socket.SHUT_RDWR)
                self.server_close()
                break

    # Overrides method from BaseServer (parent of TCPServer)
    def process_request(self, request, client_address):
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

    def get_all_online(self):
        self.lock.acquire()
        users = []
        for client_handler in self.client_handlers:
            if client_handler.username is not None:
                users.append(client_handler.username)
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

    # Add a message to the queue
    def add_message(self, message, sender="SERVER"):
        task = ["message", message, sender]
        self.queue.put(task)

    # sender is username of sender (for use in database)
    def notify_message(self, message, sender="SERVER"):
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
        self.add_message(username + " has logged in!")

    def notify_logout(self, username):
        self.add_message(username + " has logged out!")

    def shutdown_client_handler(self, client_handler):
        client_handler.shutdown()

    # Shuts down all ClientHandlers, adds task to queue telling queue worker to shutdown
    # then shuts itself down
    def shutdown_server(self):
        self.queue.put(["shutdown"])




if __name__ == "__main__":
    HOST = ''
    PORT = 9998

    # Create the server, binding to localhost on port 9999
    server = ThreadedTCPServer((HOST, PORT), ClientHandler)
    server.daemon_threads = True

    queue_worker = threading.Thread(target=server.queue_worker, name="Queue worker thread")
    queue_worker.start()

    server_thread = threading.Thread(target=server.serve_forever, name="Server socket thread")
    server_thread.start()

    try:
        while True:
            print("Waiting for input")
            _input = ""
            while _input == "":
                _input = sys.stdin.readline().strip()

            print("Got input: " + _input)

            if _input == "stop":
                break
    except KeyboardInterrupt:
        print("Got KeyboardInterrupt")
        pass

    print("Shutting down server")
    server.shutdown_server()

    print("Joining server thread")
    server_thread.join()
    print("Joining queue worker thread")
    queue_worker.join()

    print(threading.active_count())
