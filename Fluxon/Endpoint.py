from socket import gethostbyname, gethostname
import Fluxon.Routing
from Fluxon.Database.ModelsParser import ModelsParser
import pathlib
import os
import asyncio
import ssl
import threading
import logging
import pickle
import inspect
import time
import traceback
import sqlite3

def content_length(num):
    return ("0"*(5-len(str(num)))+str(num)).encode('utf-8')

class Server:
    SESSION_CONNECTION_LOOKUP = dict()

    class AsyncConnection:
        def __init__(self, peername, reader:asyncio.StreamReader, writer:asyncio.StreamWriter, server):
            self.peername = peername
            self.reader = reader
            self.write = writer
            self.server = server
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

    async def generate_response_async(self, request, connection:AsyncConnection):
        view, session, serialized_data = request.split(b"|", 2)
        if view == b'_': # receiver socket; not a request
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
            data = pickle.loads(serialized_data)
            payload = self.router.respond(
                view=view.decode('utf-8'), payload=data,
                connection=connection,
                sessionid=session.decode('utf-8')
            )
            serialized_payload = pickle.dumps(payload)
            serialized_response = connection.sessionid.encode('utf-8') + b"|" + serialized_payload
            return content_length(len(serialized_response))+serialized_response

    def __init__(self, port:int, router:Fluxon.Routing.Router, secure:bool):
        self.port = port
        self.router = router
        self.secure = secure
    
    def set_logger(self, logger:logging.Logger):
        self.logger = logger

class AsyncServer(Server):
    async def receive_request(self, reader, peername, buffer_size_limit:int=65536, timeout:int=60):
        request_content = b''
        try:
            content_length = await asyncio.wait_for(reader.read(5), timeout=timeout)
            if len(content_length) != 5:
                self.logger.warning(f"Failed to read content length from {peername}")
                return None
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
            self.logger.warning(f"Timeout after {timeout} seconds while reading from {peername}")
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
                    self.logger.info(f"Connection closed by {far_host_peername}")
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
                        self.logger.warning(f"Unable to generate an appropriate response for {writer.get_extra_info('peername')[0]}")
        except Exception as e:
            traceback.print_exc()
            self.logger.error(f"Error while handling request from {far_host_peername}: {str(e)}")
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception as e:
                self.logger.error(f"Error while closing the connection: {str(e)}")

    async def stop_server(self):
        self.server_stream.close()
        await self.server_stream.wait_closed()
        self.logger.info(f"closing server...")
    
    def terminate(self):
        pass

    async def start_server(self):
        try:
            self.host = gethostbyname(gethostname())
            if self.secure:
                self.certificatePath = os.path.join(pathlib.Path(__file__).parent, 'Certificates/ssl_tls_certificate.pem')
                self.privatKeyPath = os.path.join(pathlib.Path(__file__).parent, 'Certificates/server_private_key.pem')
                self.context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                self.context.load_cert_chain(
                    certfile=self.certificatePath, 
                    keyfile=self.privatKeyPath
                )
                self.server_stream = await asyncio.start_server(
                    self.handle_request, self.host,
                    self.port, ssl=self.context
                )
            else:
                self.server_stream = await asyncio.start_server(
                    self.handle_request, self.host, self.port
                )
            self.logger.info(f"[Fluxon] server running on {gethostbyname(gethostname())}:{self.port}")
            try: # catches CancelledError when server closed outside the event loop (remotely from "terminate" command)
                await self.server_stream.serve_forever()
            except asyncio.exceptions.CancelledError:
                self.terminate()
                self.logger.info(f"server terminated...")
        except OSError as e:
            if e.errno == 10048:
                self.logger.warning("[Fluxon] Server is already running.")

async def server_runner(server:AsyncServer, shared_data:dict):
    shared_data['event_loop'] = asyncio.get_event_loop()
    shared_data["session-connection"] = server.SESSION_CONNECTION_LOOKUP
    shared_data["models"] = server.router.models
    shared_data["database-schema-dir"] = server.router.database_schema_dir
    shared_data["database-path"] = server.router.database_path
    shared_data["session-user"] = server.router.SESSION_USER_LOOKUP
    await server.start_server()

def active_console_async(server:AsyncServer, shared_data:dict, logger:logging.Logger):
    logger.info("console activated")
    while True:
        command = input()
        # command processing goes here
        if command.lower() == "terminate":
            if 'event_loop' in shared_data:
                if isinstance(shared_data['event_loop'], asyncio.BaseEventLoop):
                    asyncio.run_coroutine_threadsafe(server.stop_server() , shared_data['event_loop'])
                else:
                    logger.error("Invalid event loop | asyncio.BaseEventLoop instance should be provided")
            else:
                logger.error("Async server event loop is missing")
        elif command.lower() == "saveschema":
            parsed_model = ModelsParser(
                models_path=shared_data["models"].__file__,
                database_schema_dir_path=shared_data["database-schema-dir"]
            )
            logger.info(f"Schema saved successfully... {parsed_model.schema_no}")
        elif command.lower().find("updateschema ") == 0:
            number = command[13:]
            sql_commands = ""
            if number.isdigit():
                file_name = "schema_"+("0"*(5-len(str(int(number)))))+str(int(number))+".sql"
                try:
                    with open(os.path.join(shared_data["database-schema-dir"], file_name)) as schema_file:
                        sql_commands = schema_file.read()
                except:
                    traceback.print_exc()
                    logger.warning(f"faild to read from {file_name}")
            else: logger.warning(f"Invalid schema number {number}")
            if sql_commands:
                conn = sqlite3.connect(shared_data["database-path"])
                cursor = conn.cursor()
                cursor.executescript(sql_commands)
                conn.commit()
                conn.close()
        else:
            try: exec(command, locals())
            except: traceback.print_exc()

def run_server(server:Server):
    caller_path = pathlib.Path(inspect.currentframe().f_back.f_code.co_filename)
    # initialize logging
    logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(asctime)s - %(message)s - %(name)s',
    handlers=[
            logging.FileHandler(os.path.join(caller_path.parent, "logs", f"{time.strftime("%Y-%m-%d~%H-%M-%S", time.localtime())}.log")),
            logging.StreamHandler()
        ]
    )
    logger = logging.getLogger(__name__)
    server.set_logger(logger)
    # run server
    if isinstance(server, AsyncServer):
        shared_data = dict() # for simple interactions between the server event loop and the console thread
        active_console_thread = threading.Thread(target=active_console_async, args=(server, shared_data, logger))
        active_console_thread.daemon = True
        active_console_thread.start()
        asyncio.run(server_runner(server, shared_data))
