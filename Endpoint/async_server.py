import threading
import asyncio
import traceback
import logging
import json
import pathlib
import os
import ssl
from Endpoint.abstract_server import Server
from Endpoint.cloud_storage_server import CloudStorageServer
from Endpoint.server_utils import content_length

# TODO add an http server, nobody using ts gang 💔🥀
class AsyncServer(Server):
    cloud_storage: CloudStorageServer
    shutdown_event = threading.Event()
    async def receive_request(self, reader, peername, buffer_size_limit:int=65536, timeout:int=60):
        request_content = b''
        try:
            content_length = await asyncio.wait_for(reader.read(5), timeout=timeout)
            if len(content_length) != 5:
                return None # corrupted request or a receiver request
            if not content_length.decode('utf-8').strip().isdigit():
                self.logger.warning(f"Invalid request format from {peername}")
                return None
            content_length = int(content_length)
            while len(request_content) < content_length:
                chunk = await asyncio.wait_for(
                    reader.read(min(content_length - len(request_content), buffer_size_limit)),
                    timeout=timeout
                )
                if not chunk:
                    self.logger.warning(f"Connection closed unexpectedly by {peername}")
                    return None
                request_content += chunk
            return request_content
        except asyncio.TimeoutError:
            return None
        except (OSError, ConnectionResetError):
            return 2

    async def handle_request(self, reader:asyncio.StreamReader, writer:asyncio.StreamWriter):
        try:
            far_host_peername = writer.get_extra_info('peername')
            connection = self.AsyncConnection(
                peername=far_host_peername,
                reader=reader, writer=writer,
                server=self
            )
            while True:
                if reader.at_eof():
                    connection.close()
                    break
                request = await self.receive_request(reader, far_host_peername)
                if request == 2:
                    connection.close()
                    break
                elif request:
                    generated_response = await self.generate_response_async(request, connection)
                    if generated_response:
                        writer.write(generated_response)
                        await writer.drain()
                    else:
                        self.logger.warning(f"[AsyncServer] Unable to generate an appropriate response for {writer.get_extra_info('peername')[0]}")
                        print(f"[AsyncServer] Unable to generate an appropriate response for {writer.get_extra_info('peername')[0]}")

        except Exception as e:
            # unexpected error handling
            connection_info = locals().get("connection", "(connection was never initialized)")
            exception_details = traceback.format_exc()
            self.logger.error(f"Error while handling request from {far_host_peername} on connection {connection_info}: {str(e)}\nTraceback: {exception_details}")
            print(f"UnexpectedError: Error while handling request from {far_host_peername} on connection {connection_info}: {e}", exception_details, sep="\n")

        finally: # edge cases safe (FIXED)
            connection = locals().get("connection", "(connection was never initialized)")
            try:
                writer.close()
                await writer.wait_closed()
                if hasattr(connection, 'is_receiver_socket'):
                    # receiver sockets are supposed to get a graceful shut down and a proper sessionid removal
                    if connection.is_receiver_socket: # getting a "yes" indicates failure, so I shall log a warning
                        logging.warning(f"Forcefully closing {connection} - proper cleanup failed")
            except ConnectionResetError:
                pass # silently ignore connection reset errors
            except Exception as e:
                # unexpected error handling
                exception_details  = traceback.format_exc()
                self.logger.error(f"Error while closing the connection {connection}: {e} traceback_message: {exception_details }")
                print(f"UnexpectedError: Error while closing the connection: {e}", exception_details , sep="\n")

    async def stop_server(self):
        self.server_stream.close()
        await self.server_stream.wait_closed()
        self.logger.info(f"[AsyncServer] Closing server...")
        print(f"[AsyncServer] Closing server...")

    def get_session_by_userid(self, userid):
        if userid in self.router.SESSION_USER_LOOKUP.values():
            for key, value in self.router.SESSION_USER_LOOKUP.items():
                if value == userid:
                    return key
        return None

    async def reverse_request(self, userid, view, data=None):
        try:
            sessionid = self.get_session_by_userid(userid)
            if sessionid:
                connection = self.SESSION_CONNECTION_LOOKUP[sessionid]
                if connection:
                    reverse_connection:Server.AsyncConnection = connection[0]
                    # sending reverse request
                    try:
                        serialized_data = json.dumps(data).encode('utf-8')
                    except:
                        serialized_data = json.dumps({"response": "ServerSideError: Invalid response"})
                        self.logger.error(f"NonSerializableResponseError: Failed to serialize {data}")
                    message = f"{view}|".encode()+serialized_data
                    reverse_connection.writer.write(content_length(len(message))+message)
                    await reverse_connection.writer.drain()
                    return True
                else:
                    return False
            else:
                return False
        except Exception as e:
            # unexpected error handling
            connection_info = locals().get("connection", "(connection was never initialized)")
            exception_details = traceback.format_exc()
            self.logger.error(f"Unexpected error while making a {view} reverse request to {userid} on connection {connection_info}: {str(e)}\nTraceback: {exception_details}")
            print(f"UnexpectedError: Unexpected error while making a {view} reverse request to {userid} on connection {connection_info}: {e}", exception_details, sep="\n")
            return False

    def terminate(self):
        """
        Called when the server terminates.
        
        Override this method to perform custom cleanup tasks. By default, it does nothing.
        """
        pass

    async def start_server(self):
        try:
            if self.secure:
                self.certificatePath = os.path.join(pathlib.Path(__file__).parent, 'Certificates/ssl_tls_certificate.pem')
                self.privateKeyPath = os.path.join(pathlib.Path(__file__).parent, 'Certificates/server_private_key.pem')
                self.context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                self.context.load_cert_chain(
                    certfile=self.certificatePath, 
                    keyfile=self.privateKeyPath
                )
                self.server_stream = await asyncio.start_server(
                    self.handle_request, self.host,
                    self.port, ssl=self.context
                )
            else:
                self.server_stream = await asyncio.start_server(
                    self.handle_request, self.host, self.port
                )
            self.logger.info(f"[AsyncServer] Server running on {self.host}:{self.port}")
            print(f"[AsyncServer] Server running on {self.host}:{self.port}")
            try: # catches CancelledError when server closed outside the event loop (remotely from "terminate" command)
                await self.server_stream.serve_forever()
            except asyncio.exceptions.CancelledError:
                self.terminate()
                self.logger.info(f"[AsyncServer] Server terminated...")
                print("[AsyncServer] Server terminated...")
        except OSError as e:
            if e.errno == 10048:
                self.logger.warning("[Fluxon] Server is already running.")
                print("[Fluxon] Server is already running.")
