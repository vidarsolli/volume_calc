import socket
import time
import sys
import threading
import os
import queue

BUFFER_SIZE = 4096
SEPARATOR = "<SEPARATOR>"

# Send all files in the image directory
def send_file(host, port, img_dir):
    print("Starting file send thread")
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((host, port))
    while True:
        img_files = [f for f in os.listdir(img_dir) if f.endswith('.jpg')]
        for img_file in img_files:
            s.listen()
            conn, addr = s.accept()
            print(f"Connection from {addr} has been established.")
            with conn:
                print(f"Sending {img_file} to {addr}")
                # get the file size
                filesize = os.path.getsize(os.path.join(img_dir, img_file))
                conn.sendall(f"{img_file}{SEPARATOR}{filesize}".encode())
                with open(os.path.join(img_dir, img_file), "rb") as f:
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
            time.sleep(0.2)
            os.remove(os.path.join(img_dir, img_file))
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
            print('Send_json onnected by', addr)
            data = str(msg).encode()
            b_data = bytearray(data)
            conn.sendall(b_data)
            conn.close()
