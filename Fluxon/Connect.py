from socket import *
import pickle
import traceback
import threading
import time

def content_length(num, padding=5):
    return ("0"*(padding-len(str(num)))+str(num)).encode()

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
                return self.establish_connection(dump)
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

    def send_request(self, view, data=b''):
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
        # establish connection
        self.establish_connection()
        # keep connection alive
        thread = threading.Thread(target=self.receiver)
        thread.start()

class CloudStorageConnector:
    def establish_connection(self):
        try:
            sock = socket(AF_INET, SOCK_STREAM)
            sock.connect((self.host, self.port))
            print("[Establish_Connection] Connection Stable (DUMP)")
            return sock
        except (ConnectionAbortedError, ConnectionError, ConnectionRefusedError, ConnectionResetError):
            print("[Establish_Connection] Failed to connect with the server; re-establish connection in one second")
            time.sleep(1)
            return self.establish_connection()

    def recv_content(self, sock, content_length, buffer_size_limit=65536):
        content_length_count = 0
        chunks = []
        while content_length > content_length_count:
            chunk = sock.recv(min(buffer_size_limit, content_length - content_length_count))
            chunks.append(chunk)
            content_length_count += len(chunk)
        return b''.join(chunks)

    def send_request(self, cloud_request, sessionid, payload=b''):
        cloud_path = cloud_request['cloud_path']
        granted_operation = cloud_request['granted_operation'].num
        try:
            message = f"{cloud_path}|{sessionid}|".encode()+payload
            sock = self.establish_connection()
            sock.send(content_length(len(message), padding=10)+message)
            if granted_operation in [0, 1, 2]: # create folder/write file/delete item
                response = sock.recv(1024).decode()
                return response
            elif granted_operation == 3: # read file
                try:
                    chunk = sock.recv(10)
                    if len(chunk) == 10:
                        content_length_, file_data = chunk[:10], chunk[10:]
                        if content_length_.isdigit():
                            content_length_ = int(content_length_) - len(file_data)
                            return file_data + self.recv_content(sock, content_length_)
                        else:
                            return False
                    else:
                        return False
                except:
                    traceback.print_exc()
                    return False
            elif granted_operation == 4: # read tree
                try:
                    chunk = sock.recv(10)
                    if len(chunk) == 10:
                        content_length_, file_data = chunk[:10], chunk[10:]
                        if content_length_.isdigit():
                            content_length_ = int(content_length_) - len(file_data)
                            return pickle.loads(file_data + self.recv_content(sock, content_length_))
                        else:
                            return False
                    else:
                        return False
                except:
                    traceback.print_exc()
                    return False
            sock.close()
        except:
            traceback.print_exc()
            print("[Send-Request] Unexpected error")

    def __init__(self, host, port):
        self.host = host
        self.port = port
