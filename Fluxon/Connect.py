from socket import *
import pickle
import traceback
import threading
import time

def content_length(num):
    return ("0"*(5-len(str(num)))+str(num)).encode()

class ConnectionHandler:
    def receive_package(self, buffer_size_limit:int=65536, timeout:int=120, sock=None):
        request_content = b''
        if not sock: sock = self.main_sock
        try:
            content_length = sock.recv(5)
            if len(content_length) != 5:
                print(f"[receive-package] Failed to read content length")
                return None
            if not content_length.decode('utf-8').isdigit():
                print(f"[receive-package] Invalid request format")
                return None
            content_length = int(content_length)
            while len(request_content) < content_length:
                chunk = sock.recv(min(content_length - len(request_content), buffer_size_limit))
                if not chunk:
                    print(f"[receive-package] Connection closed unexpectedly")
                    return None
                request_content += chunk
            return request_content
        except TimeoutError:
            traceback.print_exc()
            print(f"[receive-package] Timeout after {timeout} seconds while reading from")
            return None
        except Exception as e:
            traceback.print_exc()
            print(f"[receive-package] Error: {str(e)}")
            return None

    def handel_request(self, request):
        pass

    def establish_connection(self, dump=False):
        if dump:
            try:
                sock = socket(AF_INET, SOCK_STREAM)
                sock.connect((self.host, self.port))
                print("[Establish_Connection] Connection Stable (DUMP)")
                return sock
            except (ConnectionAbortedError, ConnectionError, ConnectionRefusedError, ConnectionResetError):
                print("[Establish_Connection] Failed to connect with the server; re-establish connection in one second")
                time.sleep(1)
                return self.establish_connection()
        else:
            try:
                self.main_sock = socket(AF_INET, SOCK_STREAM)
                # secure a session
                self.main_sock.connect((self.host, self.port))
                self.main_sock.send(b"00003_||")
                self.sessionid = self.main_sock.recv(int(self.main_sock.recv(5))).decode('utf-8')
                print("[Establish_Connection] Connection Stable", "sessionid:", self.sessionid)
            except (ConnectionAbortedError, ConnectionError, ConnectionRefusedError, ConnectionResetError):
                print("[Establish_Connection] Failed to connect with the server; re-establish connection in one second")
                time.sleep(1)
                self.establish_connection()

    def receiver(self):
        # establish connection
        self.establish_connection()
        while True:
            if not self.main_sock:
                self.establish_connection()
            try:
                while True:
                    request = self.receive_package()
                    if request:
                        if self.is_response:
                            self.is_response = False
                            self.response_ = request
                        else:
                            print("[Receiver] Server-side request detected")
                            response = self.handel_request()
                            self.main_sock.send(response)
                    else:
                        print("[Receiver] Empty package passed to the receiver; re-establish connection")
                        self.establish_connection()
            except:
                traceback.print_exc()
                print("[Receiver] Unexpected Error")

    def recv_response(self, sock):
        try:
            data = self.receive_package(sock=sock)
            sessionid, serialized_payload = data.split(b'|', 1)
            return sessionid.decode('utf-8'), pickle.loads(serialized_payload)
        except:
            traceback.print_exc()

    def send_request(self, view, data):
        try:
            serialized_data = pickle.dumps(data)
            message = f"{view}|{self.sessionid}|".encode()+serialized_data
            sock = self.establish_connection(dump=True)
            sock.send(content_length(len(message))+message)
            self.sessionid, payload = self.recv_response(sock)
            sock.close()
            return payload
        except:
            traceback.print_exc()
            print("[Send-Request] Unexpected error")

    def __init__(self, host, port):
        self.sessionid = ''
        self.main_sock = None
        self.host = host
        self.port = port
        self.is_response = False
        self.response_ = None
        # keep connection alive
        thread = threading.Thread(target=self.receiver)
        thread.start()
