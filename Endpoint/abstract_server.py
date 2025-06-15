import asyncio
import threading
import logging
import json
from socket import gethostname, gethostbyname
from Fluxon.Routing import Setup
from Fluxon.Database.db_core_interface import AsyncSQLiteDatabase
from Endpoint.server_utils import content_length
from Endpoint.async_server import AsyncServer

class Server:
    async def stop_server(self): ...
    # FIXME redis all those lookup tables soon as you hop yo ass off that windows
    SESSION_CONNECTION_LOOKUP = dict()
    shutdown_event: threading.Event

    class AsyncConnection:
        def __init__(self, peername, reader:asyncio.StreamReader, writer:asyncio.StreamWriter, server):
            self.peername = peername
            self.reader = reader
            self.writer = writer
            self.server: Server = server
            self.is_receiver_socket = False
            self.sessionid = ''

        def close(self):
            if self.sessionid in self.server.SESSION_CONNECTION_LOOKUP:
                if self in self.server.SESSION_CONNECTION_LOOKUP[self.sessionid]:
                    self.server.SESSION_CONNECTION_LOOKUP[self.sessionid].remove(self)
                    if not self.server.SESSION_CONNECTION_LOOKUP[self.sessionid]:
                        del self.server.SESSION_CONNECTION_LOOKUP[self.sessionid]
                        if self.sessionid in self.server.router.SESSION_USER_LOOKUP:
                            del self.server.router.SESSION_USER_LOOKUP[self.sessionid]

        def __str__(self):
            return f"{self.peername}/{self.sessionid}"

    async def generate_response_async(self, request: bytes, connection:AsyncConnection):
        view, session, serialized_data = request.split(b"|", 2)
        if view == b'_': # receiver socket; not a request
            connection.is_receiver_socket = True
            returned_sessionid = ''
            if connection.sessionid: # look it up
                if connection.sessionid in self.SESSION_CONNECTION_LOOKUP: # let the dude in
                    returned_sessionid = connection.sessionid
                    self.SESSION_CONNECTION_LOOKUP[connection.sessionid].append(connection)
                else: # make a him a session
                    returned_sessionid = connection.sessionid
                    self.SESSION_CONNECTION_LOOKUP[connection.sessionid] = [connection]
            else: # make him a sessionid
                returned_sessionid = self.router.generate_signed_sessionid(connection, self.router.private_key)
            returned_sessionid_ = returned_sessionid.encode('utf-8')
            return content_length(len(returned_sessionid_))+returned_sessionid_
        else:
            try:
                data = json.loads(serialized_data)
            except json.JSONDecodeError:
                self.logger.warning(f"Suspicious request received: {connection} | {serialized_data[:200]}") # connection.__str__ returns "ipaddress:port/sessionid" of the far host
                serialized_payload = json.dumps({"response": "Invalid JSON payload"})
                serialized_response = connection.sessionid.encode('utf-8') + b"|" + serialized_payload
                return content_length(len(serialized_response))+serialized_response

            payload = await self.router.respond(
                view=view.decode('utf-8'), payload=data,
                connection=connection,
                sessionid=session.decode('utf-8')
            )
            try:
                serialized_payload = json.dumps(payload).encode('utf-8')
            except:
                serialized_payload = json.dumps({"response": "ServerSideError: Invalid JSON response"})
                self.logger.error(f"NonSerializableResponseError: Failed to serialize {payload}")
            serialized_response = connection.sessionid.encode('utf-8') + b"|" + serialized_payload
            return content_length(len(serialized_response))+serialized_response

    def __init__(self, port:int, secure:bool, setup:Setup=None, cloud_storage=None, host:str=gethostbyname(gethostname())):
        self.port = port
        self.host = host
        self.secure = secure
        self.router = setup
        if isinstance(self, AsyncServer):
            if cloud_storage:
                self.cloud_storage = cloud_storage
                self.cloud_storage.cloud_folder = self.router.cloud_folder
                self.cloud_storage.cloud_auth_model = self.router.cloud_auth_model
                self.cloud_storage.main_server = self
                self.cloud_storage.cloud_database = AsyncSQLiteDatabase(
                    self.router.database_path
                )
            else:
                self.cloud_storage = None
    
    def set_logger(self, logger:logging.Logger):
        self.logger = logger
