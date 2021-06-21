#!/usr/bin/env python3

import sys
import socket
import time
import json
import selectors
import types

HOST = '127.0.0.1'  # The server's hostname or IP address
PORT = 65110        # The port used by the server
BUFFER_SIZE = 1024

while True:
    #time.sleep(1)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    print("Try connecting to ", HOST, ":", PORT)
    while s.connect_ex((HOST, PORT)) != 0:
        time.sleep(1)
        print("Retrying connecting to ", HOST, ":", PORT)

    rec = s.recv(BUFFER_SIZE)
    if len(rec) > 0:
        received = rec.decode()
        # Convert bytearray to string ande replace single quote with double quote
        received = str(received)
        received = received.replace("'", '"')
        volume_message = json.loads(received)
        volume = json.dumps(volume_message, indent=4)
        print(volume)
    s.close()