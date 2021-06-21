import socket
import time
import threading
import os
import queue

HOST = '127.0.0.1'  # Standard loopback interface address (localhost)
PORT = 65110        # Port to listen on (non-privileged ports are > 1023)
PORT2 = 65120        # Port to listen on (non-privileged ports are > 1023)
SEPARATOR = "<SEPARATOR>"
BUFFER_SIZE = 4096

json_queue = queue.Queue()

def send_file(host, port):
    print("Starting file send thread")
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((host, port))
    while True:
        time.sleep(2)
        s.listen()
        conn, addr = s.accept()
        print(f"Connection from {addr} has been established.")
        with conn:
            filename = "image.jpg"
            print(f"Sending {filename} to {addr}")
            # get the file size
            filesize = os.path.getsize(filename)
            conn.sendall(f"{filename}{SEPARATOR}{filesize}".encode())
            with open(filename, "rb") as f:
                while True:
                    # read the bytes from the file
                    bytes_read = f.read(BUFFER_SIZE)
                    if not bytes_read:
                        conn.close()
                        print("Closing connection")
                        # file transmitting is done
                        break
                    # we use sendall to assure transimission in
                    # busy networks
                    print(f"Sending {len(bytes_read)} bytes")
                    conn.sendall(bytes_read)
            # break

def send_json(host, port, msg_queue):
    global json_queue
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((host, port))
    while True:
        msg = msg_queue.get()
        s.listen()
        conn, addr = s.accept()
        with conn:
            print('Connected by', addr)
            print(str(volume_message))
            data = str(msg).encode()
            b_data = bytearray(data)
            conn.sendall(b_data)
            conn.close()


thr1 = threading.Thread(target=send_file, args=(HOST, PORT2))
thr1.start()
thr2 = threading.Thread(target=send_json, args=(HOST, PORT, json_queue))
thr2.start()

volume_message = {
    "image_name": "image.jpg",
    "time_since_detection": 0.0,
    "width": 0.0,
    "length": 0.0,
    "height": 0.0
}

i=0
last_time = time.time()
while True:
    time.sleep(1.5)
    i += 1
    volume_message["time_since_detection"] = time.time() - last_time
    last_time = time.time()
    volume_message["width"] = i * 0.13
    volume_message["length"] = i * 0.1
    volume_message["height"] = i * 0.05
    print('Sending message')
    json_queue.put(volume_message)




"""
last_time = time.time()

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind((HOST, PORT))
while True:
    time.sleep(1.5)
    s.listen()
    conn, addr = s.accept()
    i = 0
    with conn:
        print('Connected by', addr)
        i += 1
        volume_message["time_since_detection"] = time.time() - last_time
        last_time = time.time()
        volume_message["width"] = i * 0.13
        volume_message["length"] = i * 0.1
        volume_message["height"] = i * 0.05
        print(str(volume_message))
        data = str(volume_message).encode()
        b_data = bytearray(data)
        conn.sendall(b_data)
        conn.close()
"""


