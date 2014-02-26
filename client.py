'''
KTN-project 2013 / 2014
'''
import socket
from Message import *
from MessageWorker import MessageWorker
import threading
import re
import sys


class Client(object):
    def __init__(self, host, port):
        self.connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.connection.connect((host, port))

        self.login_response_event = threading.Event()

        # Start the message worker (which listens on the connection and notifies us if it has received a message)
        self.message_worker = MessageWorker(self.connection, self)
        self.message_worker.start()

        self.run = True


    # Main loop
    def start(self):
        self.username = None

        # Log in
        while self.username is None:
            new_username = self.input("Enter username: ")
            loginRequestMessage = LoginRequestMessage()
            loginRequestMessage.set_login_info(new_username)
            self.send(loginRequestMessage)

            self.login_response_event.wait()  # Blocks until message_received receives a LoginResponseMessage

        while self.run:
            new_message = self.input("")

            # Parse as cmd
            cmd = self.get_cmd(new_message)
            if cmd == 'logout':
                logoutRequestMessage = LogoutRequestMessage()
                self.send(logoutRequestMessage)
                self.run = False

            elif not cmd:
                #self.output(new_message)
                chatRequestMessage = ChatRequestMessage()
                chatRequestMessage.set_chat_message(new_message)
                self.send(chatRequestMessage)

            else:
                self.output("Invalid command!")


        self.output("Logged out, good bye!")

    def get_cmd(self, text):
        if len(text) > 0 and text[0] == '/':
            return text[1:]
        else:
            return False


    # Message is already decoded from JSON
    def message_received(self, data):
        #print "Message received from server: " + str(data)
        if "response" in data:
            if data["response"] == "login":
                # Success
                if "error" not in data:
                    self.username = data["username"]

                    for message in data["messages"]:
                        self.output(message)

                    self.login_response_event.set()


                elif data["error"] == "Invalid username!":
                    self.output("Invalid username!")


                elif data["error"] == "Name already taken!":
                    self.output("Name already taken!")

            elif data["response"] == "message":
                if not "error" in data:
                    self.output(data["message"])

                # Error: not logged in
                else:
                    self.output(data["error"])

        else:
            self.output("Server makes no sense, me don't understand!")
            pass

    def valid_username(self, username):
        match_obj = re.search('[A-z_0-9]+', username)
        return match_obj is not None and match_obj.group(0) == username

    # Server closed connection
    def connection_closed(self):
        self.message_worker.join()  # Wait for listener to exit

    def login(self):
        pass

    # data should be a Message object
    def send(self, data):
        self.connection.sendall(data.get_JSON())

    def force_disconnect(self):
        self.connection.close()

    # Output this to console
    def output(self, line):
        print line

    # Get input
    def input(self, prompt):
        print prompt,
        return sys.stdin.readline().strip()


if __name__ == "__main__":
    client = Client('www.furic.pw', 9998)
    client.start()
