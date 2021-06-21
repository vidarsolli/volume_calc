#!/usr/bin/env python3
#!/usr/bin/env python3

import sys
import socket
import os
import time
import cv2
import selectors
import types

import numpy as np

HOST = '127.0.0.1'  # The server's hostname or IP address
PORT = 65120        # The port used by the server
BUFFER_SIZE = 4096
SEPARATOR = "<SEPARATOR>"


while True:
    #time.sleep(1)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    print("Try connecting to ", HOST, ":", PORT)
    while s.connect_ex((HOST, PORT)) != 0:
        time.sleep(1)
        print("Retrying connecting to ", HOST, ":", PORT)

    rec = s.recv(BUFFER_SIZE).decode()
    print(type(rec), rec)
    received = rec
    if len(received) > 0:
        filename, filesize = received.split(SEPARATOR)
        # remove absolute path if there is
        filename = os.path.basename(filename)
        # convert to integer
        filesize = int(filesize)
        print("Receiving file: ", filename, " with size: ", filesize)
        with open("received_image.jpg", "wb") as f:
            while True:
                # read 1024 bytes from the socket (receive)
                bytes_read = s.recv(BUFFER_SIZE)
                if not bytes_read:
                    # nothing is received
                    # file transmitting is done
                    break
                # write to the file the bytes we just received
                f.write(bytes_read)
            f.close()
        img = cv2.imread("received_image.jpg")
        cv2.imshow("Overview image", img)
        cv2.waitKey(1)
    s.close()