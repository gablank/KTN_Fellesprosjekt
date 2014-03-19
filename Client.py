# -*- coding: utf-8 -*-
import sys
if sys.version_info[0] != 3:
    print("You need to run this with Python 3!")
    sys.exit(1)

import socket
from Message import *
from MessageWorker import MessageWorker
import threading
import time
import tkinter as tk


class Client(tk.Frame):
    def __init__(self, host, port, master):
        self.username = None

        tk.Frame.__init__(self, master)
        master.title("KTN Project client")
        self.config()
        self.pack()
        self.create_widgets()
        self.open_login_window()

        self.connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.connection.connect((host, port))

        self.login_response_event = threading.Event()

        # Start the message worker (which listens on the connection and notifies us if it has received a message)
        self.message_worker = MessageWorker(self.connection, self)
        self.message_worker.start()

        # Keep a list of messages client side too, for easier terminal formatting and deletion of messages
        self.messages = []

    def create_widgets(self):
        menu_bar = tk.Menu(self)
        # tearoff is some weird shit: it allows you to drag the file menu off of the main menu.
        file_menu = tk.Menu(menu_bar, tearoff=0)
        file_menu.add_command(label="Login", command=self.open_login_window)
        file_menu.add_command(label="Logout", command=self.logout)


        help_menu = tk.Menu(menu_bar, tearoff=0)
        help_menu.add_command(label="About", command=self.open_about_window)

        menu_bar.add_cascade(label="File", menu=file_menu)
        menu_bar.add_cascade(label="Help", menu=help_menu)
        self.master.config(menu=menu_bar)

        # Contains chat text and scrollbar
        self.chat_container = tk.Frame(self)

        self.chat = tk.Text(self.chat_container, {"state": tk.DISABLED})
        self.chat.pack(side=tk.LEFT)

        scrollbar = tk.Scrollbar(self.chat_container)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        scrollbar.config(command=self.chat.yview)
        self.chat.config(yscrollcommand=scrollbar.set)

        self.chat_container.pack(side=tk.TOP)

        # Input field
        self.input_field = tk.Entry(self, width="60")
        self.input_field.bind("<Return>", self.on_enter_press)
        self.input_field.pack(side=tk.BOTTOM)

        # Login window
        self.login_window = tk.Toplevel()
        self.login_window.title("Log in")

        self.login_window.protocol("WM_DELETE_WINDOW", self.hide_login_window)

        username_label = tk.Label(self.login_window, text="You need to login!\nUsername: ")
        username_label.pack()

        username_entry = tk.Entry(self.login_window)
        username_entry.bind("<Return>", self.try_login)
        username_entry.pack()

        self.login_window.attributes("-topmost", True)  # bring to front

        # About window
        self.about_window = tk.Toplevel()
        self.about_window.title("About this application")

        self.about_window.protocol("WM_DELETE_WINDOW", self.hide_login_window)
        self.about_window.withdraw()

        about_text = tk.Message(self.about_window, text="This is the client side of the KTN project for group 30.")
        about_text.pack()

        self.login_window.protocol("WM_DELETE_WINDOW", self.hide_login_window)

        close_btn = tk.Button(self.about_window, text="OK", command=self.about_window.destroy)
        close_btn.pack()

    def hide_login_window(self):
        self.login_window.withdraw()

    def hide_about_window(self):
        self.about_window.withdraw()

    def open_login_window(self):
        if self.username:
            self.output("You are already logged in!")
            return

        self.login_window.deiconify()

    def open_about_window(self):
        self.about_window.deiconify()

    def try_login(self, event):
        self.login_response_event.clear()

        new_username = event.widget.get()
        login_request_message = LoginRequestMessage()
        login_request_message.set_login_info(new_username)
        self.send_data(login_request_message)

        self.login_response_event.wait()  # Blocks until message_received receives a LoginResponseMessage

        if self.username:
            self.hide_login_window()

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

            elif cmd == "users":
                list_users_request_message = ListUsersRequestMessage()
                self.send_data(list_users_request_message)

            elif cmd == "ping":
                ping_request_message = PingRequestMessage()
                ping_request_message.set_time(time.time())
                self.send_data(ping_request_message)

            elif cmd == "uptime":
                uptime_request_message = UptimeRequestMessage()
                self.send_data(uptime_request_message)

            elif cmd == "help":
                self.output("List of commands:")
                self.output("  /logout: Log out from the server")
                self.output("  /users:  List online users")
                self.output("  /ping:   Ping the server and display the RTT")
                self.output("  /uptime: Display server uptime")
                self.output("  /help:   Display this message")

            else:
                self.output("Unknown command: /" + cmd)
                self.output("Use /help for a list of commands")

    def logout(self):
        if self.username:
            logout_request_message = LogoutRequestMessage()
            self.send_data(logout_request_message)

        root.destroy()

    def send_message(self, message):
        chat_request_message = ChatRequestMessage()
        chat_request_message.set_chat_message(message)
        self.send_data(chat_request_message)

    def get_cmd(self, text):
        if len(text) > 1 and text[0] == '/':
            return text[1:].lower()
        else:
            return False

    # Message is already decoded from JSON
    def message_received(self, data):
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

            elif data["response"] == "ping":
                time_diff = time.time() - data["time"]
                time_diff_ms = time_diff * 1000
                ping_string = "Ping: " + str(int(time_diff_ms)) + "ms"
                self.output(ping_string)

            elif data["response"] == "uptime":
                server_uptime = "Server uptime: " + data["time"]
                self.output(server_uptime)

        else:
            self.output("Server makes no sense, me don't understand!")

    # data should be a Message object
    def send_data(self, data):
        self.connection.sendall(data.get_JSON().encode("UTF-8"))

    # Output this to console
    def output(self, line):
        self.chat.config(state=tk.NORMAL)  # Need to set state to NORMAL to be able to modify the contents
        self.chat.insert(tk.END, line + "\n")  # New line has to be added
        self.chat.config(state=tk.DISABLED)
        self.chat.see(tk.END)



if __name__ == "__main__":
    root = tk.Tk()
    client = Client('www.furic.pw', 9998, root)
    #client = Client('localhost', 9998, root)
    root.protocol('WM_DELETE_WINDOW', client.logout)

    client.mainloop()
