from socket import gethostbyname, gethostname
import Fluxon.Routing
from Fluxon.Database.ModelsParser import ModelsParser
from Fluxon.Database.Manipulations import AsyncSQLiteDatabase
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
import aiofiles
import shutil

file_types_lookup = {
    # Text and Document Files
    "txt": "Text File",
    "doc": "Microsoft Word Document",
    "docx": "Microsoft Word Document (Open XML)",
    "pdf": "PDF Document",
    "rtf": "Rich Text Format",
    "odt": "OpenDocument Text Document",

    # Spreadsheet Files
    "xls": "Microsoft Excel Spreadsheet",
    "xlsx": "Microsoft Excel Spreadsheet (Open XML)",
    "csv": "Comma-Separated Values",
    "ods": "OpenDocument Spreadsheet",

    # Presentation Files
    "ppt": "Microsoft PowerPoint Presentation",
    "pptx": "Microsoft PowerPoint Presentation (Open XML)",
    "odp": "OpenDocument Presentation",

    # Image Files
    "jpg": "JPEG Image",
    "jpeg": "JPEG Image",
    "png": "Portable Network Graphics",
    "gif": "Graphics Interchange Format",
    "bmp": "Bitmap Image",
    "tiff": "Tagged Image File Format",
    "svg": "Scalable Vector Graphics",

    # Audio Files
    "mp3": "MP3 Audio",
    "wav": "Waveform Audio File Format",
    "aac": "Advanced Audio Coding",
    "flac": "Free Lossless Audio Codec",
    "ogg": "Ogg Vorbis Audio",
    "m4a": "MPEG-4 Audio",

    # Video Files
    "mp4": "MPEG-4 Video",
    "avi": "Audio Video Interleave",
    "mov": "QuickTime Movie",
    "wmv": "Windows Media Video",
    "flv": "Flash Video",
    "mkv": "Matroska Video",

    # Compressed Files
    "zip": "ZIP Archive",
    "rar": "RAR Archive",
    "7z": "7-Zip Archive",
    "tar": "Tape Archive",
    "gz": "GZIP Archive",

    # Code and Script Files
    "py": "Python Script",
    "js": "JavaScript File",
    "html": "HTML Document",
    "css": "Cascading Style Sheets",
    "java": "Java Source File",
    "c": "C Source File",
    "cpp": "C++ Source File",
    "cs": "C# Source File",
    "php": "PHP Script",
    "rb": "Ruby Script",
    "sql": "SQL File",

    # Executable and System Files
    "exe": "Windows Executable",
    "dll": "Dynamic Link Library",
    "bat": "Batch File",
    "sh": "Shell Script",
    "iso": "ISO Disc Image",

    # Miscellaneous Files
    "json": "JSON File",
    "xml": "XML File",
    "yaml": "YAML File",
    "yml": "YAML File",
    "ini": "Configuration File",
    "log": "Log File",
    "md": "Markdown File",
    "bin": "Binary File"
}

def content_length(num):
    return ("0"*(5-len(str(num)))+str(num)).encode('utf-8')

def padded_content_length(num, padding):
    return ("0"*(padding-len(str(num)))+str(num)).encode('utf-8')

def folder_structure(path):
    def build_structure(current_path):
        structure = {}
        try:
            with os.scandir(current_path) as entries:
                for entry in entries:
                    if entry.is_dir(follow_symlinks=False):
                        structure[entry.name] = build_structure(entry.path)
                    elif entry.is_file(follow_symlinks=False):
                        structure[entry.name] = 0
        except PermissionError:
            # Skip folders/files where permission is denied
            pass

        return structure

    return build_structure(path)

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
            payload = await self.router.respond(
                view=view.decode('utf-8'), payload=data,
                connection=connection,
                sessionid=session.decode('utf-8')
            )
            serialized_payload = pickle.dumps(payload)
            serialized_response = connection.sessionid.encode('utf-8') + b"|" + serialized_payload
            return content_length(len(serialized_response))+serialized_response

    def __init__(self, port:int, secure:bool, router:Fluxon.Routing.Router=None, cloud_folder:str=None, cloud_storage=None):
        self.port = port
        self.secure = secure
        if isinstance(self, AsyncServer):
            self.router = router
            if cloud_storage:
                self.cloud_storage = cloud_storage
                self.cloud_storage.main_server = self
                self.cloud_storage.cloud_database = AsyncSQLiteDatabase(
                    self.router.database_path
                )
        if isinstance(self, CloudStorageServer):
            self.cloud_folder = cloud_folder
    
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

class CloudStorageServer(Server):
    async def stream_file(self, file_path, chunk_size):
        async with aiofiles.open(file_path, 'rb') as file:
            while chunk := file.read(chunk_size):
                yield chunk

    async def get_file_path_by_id(self):
        return r"C:\Users\skhodari\Desktop\TESTING\cloud_folder\test.txt"

    async def get_file_metadata(path):
        # Offloading to a separate thread
        return await asyncio.get_event_loop().run_in_executor(None, os.stat, path)

    async def get_directory_id(self, dir_path, owner_id=False):
        current_folder_id = None
        owner_id_ = None
        columns = ['id', 'owner'] if owner_id else ['id']
        for parent in dir_path.__str__().replace("\\", '/').split("/"):
            query = await self.cloud_database.Directory.Check(self.cloud_database.where[
                (self.cloud_database.Directory.name == parent) & (self.cloud_database.Directory.directory == current_folder_id)
            ], fetch=1, columns=columns)
            if query:
                current_folder_id = query[0][0]
                if owner_id:
                    owner_id_ = query[0][1]
            else:
                logging.error(f"[CloudStorage] Failed to get directory id ({dir_path})")
        return (current_folder_id, owner_id_) if owner_id else current_folder_id

    async def handle_request(self, reader:asyncio.StreamReader, writer:asyncio.StreamWriter):
        try:
            far_host_peername = writer.get_extra_info('peername')
            content_length_count = 0
            headers_length = 0
            content_length = await asyncio.wait_for(reader.read(10), timeout=self.timeout)
            if len(content_length) != 10:
                self.logger.warning(f"Failed to read content length from {far_host_peername}")
                return None
            if not content_length.decode('utf-8').strip().isdigit():
                self.logger.warning(f"Invalid request format from {far_host_peername}")
                return None
            content_length = int(content_length)
            header_chunk = await asyncio.wait_for(
                reader.read(min(content_length - content_length_count, self.buffer_size_limit)),
                timeout=self.timeout
            )
            if not header_chunk:
                self.logger.warning(f"Connection closed unexpectedly by {far_host_peername}")
                return None
            content_length_count += len(header_chunk)
            encoded_cloud_relative_path, encoded_session_id, file_data = header_chunk.split(b"|",2)
            headers_length += len(encoded_cloud_relative_path) + len(encoded_session_id) + 2
            cloud_relative_path = encoded_cloud_relative_path.decode()
            session_id = encoded_session_id.decode()
            if (cloud_relative_path, session_id) in self.operation_keys:
                operation = self.operation_keys[cloud_relative_path, session_id]
                operation_path = os.path.join(self.cloud_folder, cloud_relative_path)
                # OPERATION 0 Create directory
                if operation == 0:
                    try:
                        os.mkdir(operation_path)
                        # record operation in database
                        directory_path = pathlib.Path(cloud_relative_path)
                        parent_directory_id, owner_id = await self.get_directory_id(directory_path.parent, owner_id=True)
                        await self.cloud_database.Directory.Insert({
                            "name": directory_path.name,
                            "owner": owner_id,
                            "directory": parent_directory_id
                        })
                        # report success to client
                        writer.write(b"success")
                        await writer.drain()
                        return None
                    except:
                        traceback.print_exc()
                        if writer.can_write_eof():
                            writer.write(b"[CloudStorage] Unable to create directory")
                            await writer.drain()
                        return None
                # OPERATION 1 Write file
                elif operation == 1:
                    try:
                        # Write received stream
                        async with aiofiles.open(operation_path, 'wb') as file:
                            if file_data:
                                await file.write(file_data)
                            while content_length_count < content_length:
                                try:
                                    chunk = await asyncio.wait_for(
                                        reader.read(min(content_length - content_length_count, self.buffer_size_limit)),
                                        timeout=self.timeout
                                    )
                                except asyncio.TimeoutError:
                                    self.logger.error(f"Timeout while reading data from {far_host_peername}")
                                    return None
                                if not chunk:
                                    self.logger.warning(f"Connection closed unexpectedly by {far_host_peername}")
                                    return None
                                content_length_count += len(chunk)
                                await file.write(chunk)
                        # Record operation in database
                        try:
                            parent_directory_id, owner_id = await self.get_directory_id(
                                dir_path=pathlib.Path(cloud_relative_path).parent,
                                owner_id=True
                            )
                            # delete prev records
                            await self.cloud_database.File.Delete(self.cloud_database.where[
                                (self.cloud_database.File.name == pathlib.Path(cloud_relative_path).name) & (self.cloud_database.File.directory == parent_directory_id)
                            ])
                            # add newest file record
                            file_id = await self.cloud_database.File.Insert({
                                'directory': parent_directory_id,
                                'name': pathlib.Path(cloud_relative_path).name,
                                'owner': owner_id,
                                'size': content_length_count - headers_length,
                                'file_type': file_types_lookup[pathlib.Path(cloud_relative_path).name.split('.')[-1]]
                            })
                            if file_id:
                                # Report success to client
                                writer.write(b"success")
                                await writer.drain()
                                return None
                            else:
                                logging.error(f"[CloudStorage] Failed to record write file operation ({cloud_relative_path})")
                        except:
                            logging.error(f"[CloudStorage] Failed to update records for write file operation | ({cloud_relative_path})")
                            traceback.print_exc()
                            return None
                    except:
                        traceback.print_exc()
                        writer.write(b"[CloudStorage] Unable to write file")
                        await writer.drain()
                        return None
                # OPERATION 2 Delete Item
                elif operation == 2:
                    try:
                        item = pathlib.Path(operation_path)
                        if item.exists():
                            if item.is_dir(): # If item is a floder
                                shutil.rmtree(item)
                                # Remove folder from cloud records
                                directory_id = await self.get_directory_id(dir_path=cloud_relative_path)
                                if directory_id:
                                    # delete records
                                    await self.cloud_database.Directory.Delete(self.cloud_database.where[self.cloud_database.Directory.id == directory_id])
                                    # report success to client
                                    writer.write(b"success")
                                    await writer.drain()
                                    return None
                                else:
                                    logging.error(f"DirectoryNotFound: Failed to get directory id ({cloud_relative_path})")
                                    return None
                            elif item.is_file(): # If item is a file
                                os.remove(item)
                                # Remove file from cloud records
                                parent_directory_id = await self.get_directory_id(dir_path=pathlib.Path(cloud_relative_path).parent)
                                if parent_directory_id:
                                    # delete records
                                    await self.cloud_database.File.Delete(self.cloud_database.where[
                                        (self.cloud_database.File.name == pathlib.Path(cloud_relative_path).name) & (self.cloud_database.File.directory == parent_directory_id)
                                    ])
                                    # report success to client
                                    writer.write(b"success")
                                    await writer.drain()
                                    return None
                                else:
                                    logging.error(f"DirectoryNotFound: Failed to get parent directory id ({cloud_relative_path})")
                                    return None
                        else:
                            writer.write(b"[CloudStorage] Item not found.")
                            await writer.drain()
                            return None
                    except FileNotFoundError:
                        writer.write(b"[CloudStorage] Item not found.")
                        await writer.drain()
                        return None
                    except:
                        writer.write(f"[CloudStorage] Unable to delete item ({item.absolute()})".encode())
                        await writer.drain()
                        return None
                # OPERATION 3 Read file
                elif operation == 3:
                    file_path = pathlib.Path(operation_path)
                    if file_path.is_file():
                        # get file size
                        parent_directory_id = await self.get_directory_id(pathlib.Path(cloud_relative_path).parent)
                        query = await self.cloud_database.File.Check(self.cloud_database.where[
                            (self.cloud_database.File.name == file_path.name) & (self.cloud_database.File.directory == parent_directory_id)
                        ], fetch=1, columns=['size'])
                        if query:
                            file_size = int(query[0][0])
                            # send content length
                            writer.write(padded_content_length(file_size, 10))
                            await writer.drain()
                            # send file stream
                            writer_drain_count = 0  # drain every 15 MB
                            async with aiofiles.open(file_path, 'rb') as file:
                                file_chunk = await file.read(1024 * 1024) # 1 MB at a time
                                while file_chunk:
                                    try:
                                        writer.write(file_chunk)
                                        writer_drain_count += 1
                                        if writer_drain_count == 15:
                                            await writer.drain()
                                            writer_drain_count = 0
                                        file_chunk = await file.read(self.buffer_size_limit)
                                    except:
                                        traceback.print_exc()
                                        self.logger.error(f"Unexpected error while sending data to {far_host_peername}")
                                        return None
                        else:
                            writer.write(("0"*10+f"InvalidOperation: path provided ({file_path.absolute()}) is not a file").encode())
                            await writer.drain()
                            return None
                    else:
                        writer.write(("0"*10+f"InvalidOperation: path provided ({file_path.absolute()}) is not a file").encode())
                        await writer.drain()
                        return None
                # OPERATION 4 Read tree
                elif operation == 4:
                    if pathlib.Path(operation_path).is_dir():
                        try:
                            tree = folder_structure(pathlib.Path(operation_path))
                            serialized_tree = pickle.dumps(tree)
                            writer.write(padded_content_length(len(serialized_tree), 10))
                            writer.write(serialized_tree)
                            await writer.drain()
                            return None
                        except:
                            traceback.print_exc()
                            print("UnexpectedError: Error while preparing read tree operation")
                    else:
                        writer.write(("0"*10+f"InvalidOperation: path provided ({file_path.absolute()}"))
                        await writer.drain()
                        return None
            else:
                writer.write(b"[CloudStorage] AccessDenied: Invalid operation keys")
        except asyncio.TimeoutError:
            self.logger.warning(f"Timeout after {self.timeout} seconds while reading from {far_host_peername}")
            return None
        except (OSError, ConnectionResetError):
            self.logger.warning(f"Connection closed unexpectedly by {far_host_peername}")
            return None
        except Exception as e:
            traceback.print_exc()
            self.logger.error(f"Error while handling request from {far_host_peername}: {str(e)}")
        finally:
            # delete operation
            if (cloud_relative_path, session_id) in self.operation_keys:
                del self.operation_keys[cloud_relative_path, session_id]
            # close connection
            writer.close()
            await writer.wait_closed()

    async def stop_server(self):
        self.server_stream.close()
        await self.server_stream.wait_closed()
        self.logger.info(f"closing server...")
    
    def terminate(self):
        # for future cleanup
        pass

    async def start_server(self):
        try:
            self.host = gethostbyname(gethostname())
            self.timeout = 60
            self.buffer_size_limit = 65536
            self.operation_keys = dict()
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
            self.logger.info(f"[CloudStorage] cloud storage running on {gethostbyname(gethostname())}:{self.port}")
            try: # catches CancelledError when server closed outside the event loop (remotely from "terminate" command)
                await self.server_stream.serve_forever()
            except asyncio.exceptions.CancelledError:
                self.terminate()
                self.logger.info(f"server terminated...")
        except OSError as e:
            if e.errno == 10048:
                self.logger.warning("[CloudStorage] Server is already running.")

def run_cloud_storage_server(cloud_server, shared_data):
    asyncio.run(server_runner(cloud_server, shared_data))

async def server_runner(server:AsyncServer, shared_data:dict):
    if isinstance(server, AsyncServer):
        if server.cloud_storage:
            server.cloud_storage.set_logger(server.logger)
            cloud_server_thread = threading.Thread(target=run_cloud_storage_server, args=(server.cloud_storage, shared_data))
            cloud_server_thread.start()
        shared_data['main-server'] = server
        shared_data['cloud-storage'] = server.cloud_storage
        shared_data['event_loop'] = asyncio.get_event_loop()
        shared_data["session-connection"] = server.SESSION_CONNECTION_LOOKUP
        shared_data["models"] = server.router.models
        shared_data["database-schema-dir"] = server.router.database_schema_dir
        shared_data["database-path"] = server.router.database_path
        shared_data["session-user"] = server.router.SESSION_USER_LOOKUP
        await server.start_server()
    elif isinstance(server, CloudStorageServer):
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
                    logger.warning(f"Failed to read from {file_name}")
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
            logging.FileHandler(os.path.join(caller_path.parent, "logs", f"{time.strftime('%Y-%m-%d~%H-%M-%S', time.localtime())}.log")),
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
