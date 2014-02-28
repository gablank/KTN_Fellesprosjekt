# -*- coding: utf-8 -*-

import json
import sys


if sys.version_info[0] != 3:
    print("You need to run this with Python 3!")
    sys.exit(1)

class MessageException(Exception):
    pass


class Message(object):
    def __init__(self):
        self.message_attributes = {}
        self.complete = False

    def complete_guard(self):
        if self.complete:
            raise MessageException("Message already complete!")

    def get_JSON(self):
        if not self.complete:
            raise MessageException("Attempted to pack unfinished message!")

        return json.dumps(self.message_attributes)


class LoginRequestMessage(Message):
    def __init__(self):
        super(LoginRequestMessage, self).__init__()
        self.message_attributes["request"] = "login"

    def set_login_info(self, username):
        self.complete_guard()
        self.message_attributes["username"] = username
        self.complete = True


class LoginResponseMessage(Message):
    def __init__(self):
        super(LoginResponseMessage, self).__init__()
        self.message_attributes["response"] = "login"

    def set_success(self, username, message_log):
        self.complete_guard()
        self.message_attributes["username"] = username
        self.message_attributes["messages"] = message_log
        self.complete = True

    def set_invalid_username(self, username):
        self.complete_guard()
        self.message_attributes["username"] = username
        self.message_attributes["error"] = "Invalid username!"
        self.complete = True

    def set_taken_username(self, username):
        self.complete_guard()
        self.message_attributes["username"] = username
        self.message_attributes["error"] = "Name already taken!"
        self.complete = True


class ChatRequestMessage(Message):
    def __init__(self):
        super(ChatRequestMessage, self).__init__()
        self.message_attributes["request"] = "message"

    def set_chat_message(self, message):
        self.complete_guard()
        self.message_attributes["message"] = message
        self.complete = True


class ChatResponseMessage(Message):
    def __init__(self):
        super(ChatResponseMessage, self).__init__()
        self.message_attributes["response"] = "message"

    def set_success(self, message):
        self.complete_guard()
        self.message_attributes["message"] = message
        self.complete = True

    def set_not_logged_in(self):
        self.complete_guard()
        self.message_attributes["error"] = "You are not logged in!"
        self.complete = True


class LogoutRequestMessage(Message):
    def __init__(self):
        super(LogoutRequestMessage, self).__init__()
        self.message_attributes["request"] = "logout"
        self.complete = True


class LogoutResponseMessage(Message):
    def __init__(self):
        super(LogoutResponseMessage, self).__init__()
        self.message_attributes["response"] = "logout"

    def set_success(self, username):
        self.complete_guard()
        self.message_attributes["username"] = username
        self.complete = True

    def set_not_logged_in(self, username):
        self.complete_guard()
        self.message_attributes["username"] = username
        self.message_attributes["error"] = "Not logged in!"
        self.complete = True


class ProtocolErrorMessage(Message):
    def __init__(self):
        super(ProtocolErrorMessage, self).__init__()
        self.message_attributes["response"] = "protocolError"

    def set_error_message(self, message):
        self.complete_guard()
        self.message_attributes["error"] = message
        self.complete = True


class ListUsersRequestMessage(Message):
    def __init__(self):
        super(ListUsersRequestMessage, self).__init__()
        self.message_attributes["request"] = "listUsers"
        self.complete = True


class ListUsersResponseMessage(Message):
    def __init__(self):
        super(ListUsersResponseMessage, self).__init__()
        self.message_attributes["response"] = "listUsers"

    def set_users(self, users):
        self.complete_guard()
        self.message_attributes["users"] = users
        self.complete = True


# Testing
if __name__ == "__main__":
    print("Testing LoginRequestMessage")
    loginRequestMessage = LoginRequestMessage()

    try:
        loginRequestMessage.get_JSON()
    except MessageException:
        print("Guard test #1 successful")
    else:
        print("Guard test #1 unsuccessful")

    loginRequestMessage.set_login_info("anders")

    try:
        loginRequestMessage.set_login_info("anders")
    except MessageException:
        print("Guard test #2 successful")
    else:
        print("Guard test #2 unsuccessful")

    print("LoginRequestMessage: " + loginRequestMessage.get_JSON())
