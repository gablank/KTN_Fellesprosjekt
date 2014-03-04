# -*- coding: utf-8 -*-
import sys
if sys.version_info[0] != 3:
    print("You need to run this with Python 3!")
    sys.exit(1)

import socket
from Message import *
from MessageWorker import MessageWorker
import threading
import re
import time
import tkinter as tk


class Client(tk.Frame):
    def __init__(self, host, port, master):
        self.gui = master is not None

        self.username = None
        self.login_window = None


        if self.gui:
            tk.Frame.__init__(self, master)
            master.title("KTN Project client")
            self.config()
            self.pack()
            self.createWidgets()


        self.connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.connection.connect((host, port))

        self.login_response_event = threading.Event()

        # Start the message worker (which listens on the connection and notifies us if it has received a message)
        self.message_worker = MessageWorker(self.connection, self)
        self.message_worker.start()

        # Keep a list of messages client side too, for easier terminal formatting and deletion of messages
        self.messages = []


        self.run = True


    def createWidgets(self):
        menu_bar = tk.Menu(self)
        # tearoff is some weird shit: it allows you to drag the file menu off of the main menu.
        file_menu = tk.Menu(menu_bar, tearoff=0)
        file_menu.add_command(label="Login", command=self.login)
        file_menu.add_command(label="Logout", command=self.logout)


        help_menu = tk.Menu(menu_bar, tearoff=0)
        help_menu.add_command(label="About", command=self.about)

        menu_bar.add_cascade(label="File", menu=file_menu)
        menu_bar.add_cascade(label="Help", menu=help_menu)
        self.master.config(menu=menu_bar)

        # Contains chat text and scrollbar
        self.chatContainer = tk.Frame(self)

        self.chat = tk.Text(self.chatContainer, {"state": tk.DISABLED})
        self.chat.pack(side=tk.LEFT)

        scrollbar = tk.Scrollbar(self.chatContainer)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        scrollbar.config(command=self.chat.yview)
        self.chat.config(yscrollcommand=scrollbar.set)

        self.chatContainer.pack(side=tk.TOP)


        # Input field
        self.input_field = tk.Entry(self, width="60")
        self.input_field.bind("<Return>", self.on_enter_press)
        self.input_field.pack(side=tk.BOTTOM)

        self.login()

    # Main loop
    '''def start(self):
        self.username = None

        # Log in
        while self.username is None:
            self.login_response_event.clear()

            new_username = self.input("Enter username: ")

            if self.valid_username(new_username):
                loginRequestMessage = LoginRequestMessage()
                loginRequestMessage.set_login_info(new_username)
                self.send_data(loginRequestMessage)

                self.login_response_event.wait()  # Blocks until message_received receives a LoginResponseMessage

            else:
                self.output("Client: Invalid username!")

        while self.run:
            new_message = self.input("> ")

            # Parse as cmd
            cmd = self.get_cmd(new_message)

            if not cmd:
                now_string = time.strftime("%H:%M:%S")
                self.output(self.username + " " + now_string + ": " + new_message)
                chatRequestMessage = ChatRequestMessage()
                chatRequestMessage.set_chat_message(new_message)
                self.send_data(chatRequestMessage)

            else:
                if cmd == "logout":
                    logoutRequestMessage = LogoutRequestMessage()
                    self.send_data(logoutRequestMessage)
                    self.run = False

                elif cmd == "listusers":
                    listUsersRequestMessage = ListUsersRequestMessage()
                    self.send_data(listUsersRequestMessage)

                else:
                    self.output("Unknown command: /" + cmd)

        self.output("Logged out, good bye!")'''

    def destroy_window(self, window):
        window.destroy()
        window = None
        pass

    def login(self):
        if self.username:
            self.output("You are already logged in!")
            return

        if self.login_window:
            self.login_window.focus()
            return

        self.login_window = tk.Toplevel()
        self.login_window.title("Log in")
        self.login_window.protocol("WM_DELETE_WINDOW", self.destroy_window(self.login_window))

        self.output(str(self.login_window.attributes()))

        username_label = tk.Label(self.login_window, text="You need to login!\nUsername: ")
        username_label.pack()

        username_entry = tk.Entry(self.login_window)
        username_entry.bind("<Return>", self.try_login)
        username_entry.pack()

        self.login_window.attributes("-topmost", True)  # bring to front

    def try_login(self, event):
        self.login_response_event.clear()

        new_username = event.widget.get()
        loginRequestMessage = LoginRequestMessage()
        loginRequestMessage.set_login_info(new_username)
        self.send_data(loginRequestMessage)

        self.login_response_event.wait()  # Blocks until message_received receives a LoginResponseMessage

        if self.username:
            self.login_window.destroy()

    def on_enter_press(self, event):
        text = self.input_field.get()
        self.input_field.delete(0, tk.END)  # Empty the Entry field

        self.handle_input(text)

    def handle_input(self, input_text):
        # Parse as cmd
        cmd = self.get_cmd(input_text)

        if not cmd:
            self.send_message(input_text)

        else:
            if cmd == "logout":
                self.logout()

            elif cmd == "listusers":
                listUsersRequestMessage = ListUsersRequestMessage()
                self.send_data(listUsersRequestMessage)

            else:
                self.output("Unknown command: /" + cmd)

    def about(self):
        about_window = tk.Toplevel()
        about_window.title("About this application")
        about_text = tk.Message(about_window, text="This is the client side of the KTN project for group 30.")
        about_text.pack()

        close_btn = tk.Button(about_window, text="OK", command=about_window.destroy)
        close_btn.pack()

    def logout(self):
        if self.username:
            logoutRequestMessage = LogoutRequestMessage()
            self.send_data(logoutRequestMessage)

        self.run = False

        if self.gui:
            root.destroy()

    def send_message(self, message):
        chatRequestMessage = ChatRequestMessage()
        chatRequestMessage.set_chat_message(message)
        self.send_data(chatRequestMessage)


    def get_cmd(self, text):
        if len(text) > 1 and text[0] == '/':
            return text[1:].lower()
        else:
            return False

    # Message is already decoded from JSON
    def message_received(self, data):
        # print("Message received from server: " + str(data))
        if "response" in data:
            if data["response"] == "login":
                # Success
                if "error" not in data:
                    self.username = data["username"]

                    # Notify main thread
                    # Note: This has to be before the output calls (at least when using a GUI)
                    self.login_response_event.set()

                    self.output("Logged in as " + self.username)

                    self.messages = data["messages"]

                    for message in self.messages:
                        msg_id, msg, sender, timestamp = message
                        # Print the UNIX timestamp (message[3]) pretty as hh:mm:ss
                        now_pretty_print = time.strftime("%H:%M:%S", time.localtime(int(timestamp)))
                        self.output("[" + str(msg_id) + "] " + sender + " @ " + now_pretty_print + ": " + msg)

                elif data["error"] == "Invalid username!":
                    # Notify main thread
                    # Note: This has to be before the output calls (at least when using a GUI)
                    self.login_response_event.set()
                    self.output("Invalid username!")

                elif data["error"] == "Name already taken!":
                    # Notify main thread
                    # Note: This has to be before the output calls (at least when using a GUI)
                    self.login_response_event.set()
                    self.output("Name already taken!")



            elif data["response"] == "message":
                if not "error" in data:
                    msg_id, msg, sender, timestamp = data["message"]
                    # Print the UNIX timestamp (message[3]) pretty as hh:mm:ss
                    now_pretty_print = time.strftime("%H:%M:%S", time.localtime(int(timestamp)))
                    self.output("[" + str(msg_id) + "] " + sender + " @ " + now_pretty_print + ": " + msg)

                # Error: not logged in
                else:
                    self.output(data["error"])

            elif data["response"] == "listUsers":
                users_online_string = "Online users: " + ", ".join(data["users"])
                self.output(users_online_string)

        else:
            self.output("Server makes no sense, me don't understand!")

    def valid_username(self, username):
        match_obj = re.search(u'[A-zæøåÆØÅ_0-9]+', username)
        return match_obj is not None and match_obj.group(0) == username

    # Server closed connection
    def connection_closed(self):
        self.message_worker.join()  # Wait for listener to exit

    # data should be a Message object
    def send_data(self, data):
        self.connection.sendall(data.get_JSON().encode("UTF-8"))

    def force_disconnect(self):
        self.connection.close()

    # Output this to console
    def output(self, line):
        if self.gui:
            self.chat.config(state=tk.NORMAL)  # Need to set state to NORMAL to be able to modify the contents
            self.chat.insert(tk.END, line + "\n")  # New line has to be added
            self.chat.config(state=tk.DISABLED)
            self.chat.see(tk.END)
        else:
            print("\r" + line)

    # Get input
    def input(self, prompt):
        print("\r" + prompt)
        return sys.stdin.readline().strip()


if __name__ == "__main__":
    root = tk.Tk()
    client = Client('www.furic.pw', 9998, root)
    root.protocol('WM_DELETE_WINDOW', client.logout)
    # client = Client('localhost', 9999, root)

    client.mainloop()
