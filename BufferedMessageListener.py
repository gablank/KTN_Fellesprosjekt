class BufferedMessageListener(object):
    def __init__(self, connection):
        self.connection = connection
        self.recv_buffer = ""

    # Receive data until we have one or more COMPLETE JSON objects to deliver
    # Returns: Exactly *ONE* JSON object (as string)
    # or False if connection was closed
    def receive_message(self):
        num_brackets = 0  # "Net worth" of brackets, that is: Number of { minus number of }
        buffer_pos = 0  # How far in the buffer we've searched for an object
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
                buffer_pos = i + 1
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
                    object_json = self.recv_buffer[:i + 1]
                    self.recv_buffer = self.recv_buffer[i + 1:]

                    return object_json

            # We don't have an object to serve; wait for more data
            received_bytes = self.connection.recv(1024)

            # Connection was closed
            if len(received_bytes) == 0:
                return False

            # Decode received bytes as utf-8
            received_as_string = received_bytes.decode("utf-8")

            self.recv_buffer += received_as_string