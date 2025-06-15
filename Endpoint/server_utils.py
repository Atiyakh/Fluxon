import os
import asyncio
import logging
import threading
import traceback
from Endpoint.async_server import AsyncServer
from Endpoint.cloud_storage_server import CloudStorageServer
from Endpoint.interactive_console import interactive_console
from Fluxon.Database.db_core_interface import AsyncSQLiteDatabase
from Endpoint.server_utils import console_server_terminate
from Endpoint.abstract_server import Server

# custom exceptions
class ServerExternalShutdown(Exception):
    """signals external group shutdown."""
    pass

class InvalidEventLoop(Exception):
    """Raised when an invalid event loop is provided."""
    pass

# Lookup table for file types and their descriptions
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

async def run_cloud_storage_server_tasks(
        cloud_server:CloudStorageServer,
        shared_data: dict
    ):
    try:
        # run the cloud storage server in an asyncio event loop
        _, pending = await asyncio.wait([
            asyncio.create_task(server_startup(cloud_server, shared_data)),
            asyncio.create_task(cloud_server.shutdown_worker())
        ], return_when=asyncio.FIRST_EXCEPTION)
        # clean up pending tasks
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
    except Exception as e:
        traceback.print_exc()
        cloud_server.logger.error(f"Error while running the server: {e}\nTraceback: {traceback.format_exc()}")
        print(f"Error while running the server: {e}")

def cloud_server_thread_startup(
        cloud_server:CloudStorageServer,
        shared_data:dict
    ):  # FIXME: unify logging pattern with the main server
    # start an event loop for this thread
    try:
        asyncio.set_event_loop(asyncio.new_event_loop())
        asyncio.get_event_loop().run_until_complete(
            run_cloud_storage_server_tasks(cloud_server, shared_data)
        )
    except Exception as e:
        traceback.print_exc()
        cloud_server.logger.error(f"Error while running the cloud server: {e}\nTraceback: {traceback.format_exc()}")
        print(f"Error while running the cloud server: {e}")

def console_server_terminate(server:Server, shared_data:dict, logger:logging.Logger):
    if 'event_loop' in shared_data:
        if isinstance(shared_data['event_loop'], asyncio.BaseEventLoop):
            asyncio.run_coroutine_threadsafe(server.stop_server() , shared_data['event_loop'])
        else:
            logger.error("InvalidEventLoop | asyncio.BaseEventLoop instance should be provided")
            print("ERROR: InvalidEventLoop | asyncio.BaseEventLoop instance should be provided")
            raise InvalidEventLoop(
                "asyncio.BaseEventLoop object not provided"
            )
    else:
        logger.error("Async server event loop is missing | 'event_loop' from shared_data not found")
        print("ERROR: Async server event loop is missing | 'event_loop' from shared_data not found")
        raise InvalidEventLoop(
            "asyncio.BaseEventLoop object not provided"
        )

async def server_startup(server:Server, shared_data:dict):
    # run server
    if isinstance(server, AsyncServer):
        # main server setup
        if isinstance(server.cloud_storage, CloudStorageServer):
            server.cloud_storage.set_logger(server.logger)
            cloud_server_thread = threading.Thread(target=cloud_server_thread_startup, args=(server.cloud_storage, shared_data))
            cloud_server_thread.start()
        # shared data setup
        shared_data['main-server'] = server
        shared_data['logger'] = server.logger
        shared_data['cloud-storage'] = server.cloud_storage
        shared_data['event_loop'] = asyncio.get_running_loop() # main server event loop (on the main thread)
        shared_data["session-connection"] = server.SESSION_CONNECTION_LOOKUP
        shared_data["models"] = server.router.models
        shared_data["database-schema-dir"] = server.router.database_schema_dir
        shared_data["database-path"] = server.router.database_path
        shared_data["session-user"] = server.router.SESSION_USER_LOOKUP
        # activate console in the background
        print("[Fluxon] Console activated...")
        active_console_thread = threading.Thread(target=interactive_console, args=(server, shared_data, server.logger), daemon=True)
        active_console_thread.start()
        # initiate database api and run server
        server.database = AsyncSQLiteDatabase(shared_data["database-path"])
    await server.start_server()

def run_server(server: Server):
    # retrieve main logger
    logger = logging.getLogger("main_logger")
    server.set_logger(logger)
    # run server
    if isinstance(server, AsyncServer):
        shared_data = dict() # for simple interactions between the server event loop and the console thread
        # run server
        current_event_loop = asyncio.get_event_loop()
        try:
            current_event_loop.run_until_complete(server_startup(server, shared_data))
        except KeyboardInterrupt:
            server.shutdown_event.set()  # signal the shutdown worker to stop
            console_server_terminate(server, shared_data, logger)
            print("[Fluxon] Server terminated... [KeyboardInterrupt]")
        except Exception as e:
            traceback.print_exc()
            logger.error(f"Error while running the server: {e}")
            print(f"Error while running the server: {e}")
