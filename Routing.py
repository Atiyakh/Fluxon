import uuid
import hmac
import hashlib
import base64
from collections.abc import Coroutine

SESSION_USER_LOOKUP = dict()

def generate_signed_sessionid(connection, private_key):
    session_id = str(uuid.uuid4())
    signature = hmac.new(private_key.encode(), session_id.encode(), hashlib.sha256).digest()
    encoded_signature = base64.urlsafe_b64encode(signature).decode('utf-8').rstrip("=")
    signed_sessionid = f"{session_id}.{encoded_signature}"
    # Make sure the sessionid is not already registered
    if signed_sessionid in connection.server.SESSION_CONNECTION_LOOKUP:
        return generate_signed_sessionid(connection, private_key)
    else:
        connection.server.SESSION_CONNECTION_LOOKUP[signed_sessionid] = [connection]
        connection.sessionid = signed_sessionid
        return signed_sessionid

class Request:
    def __auth(self):
        if not self.connection.sessionid:
            if self.sessionid:
                if self.sessionid in self.connection.server.SESSION_CONNECTION_LOOKUP:
                    if self.connection in self.connection.server.SESSION_CONNECTION_LOOKUP[self.sessionid]:
                        self.connection.sessionid = self.sessionid
                    else:
                        self.connection.server.SESSION_CONNECTION_LOOKUP[self.sessionid].append(self.connection)
                        self.connection.sessionid = self.sessionid
                else: # invalid sessionid; make him another one
                    self.sessionid = generate_signed_sessionid(self.connection, self.connection.server.router.private_key)
            else: # the dude aint got nothin; bake him a sessionid
                self.sessionid = generate_signed_sessionid(self.connection, self.connection.server.router.private_key)
        if self.connection.sessionid in SESSION_USER_LOOKUP:
            self.connection.userid = SESSION_USER_LOOKUP[self.connection.sessionid]
            self.userid = SESSION_USER_LOOKUP[self.connection.sessionid]
        else:
            self.userid = None
            self.connection.userid = None

    def login(self, id_):
        if self.connection.sessionid:
            session_removed = [session for session, user_id in SESSION_USER_LOOKUP.items() if user_id == id_]
            for session in session_removed:
                del SESSION_USER_LOOKUP[session]
            SESSION_USER_LOOKUP[self.connection.sessionid] = id_
            return True
        else:
            print(" - Failed to login [INVALID SESSION]")
            return False

    def grant_access(self, granted_operation, cloud_relative_path):
        if self.connection.server.cloud_storage:
            if self.connection.userid:
                self.connection.server.cloud_storage.operation_keys[(cloud_relative_path, self.connection.sessionid)] = granted_operation.num
            else:
                self.connection.server.logger.warning(f"Invalid operation {granted_operation}")
        else:
            raise ModuleNotFoundError(
                "[Fluxon] Cloud storage server not found"
            )

    def __init__(self, payload, connection, sessionid, cloud_operations):
        self.connection = connection
        self.cloud_operations = cloud_operations
        self.payload = payload
        self.sessionid = sessionid
        self.server = connection.server
        self.__auth()

# cloud operation flags
class create_directory_: num = 0
class write_file_: num = 1
class delete_item_: num = 2
class read_file_: num = 3
class read_tree_: num = 4

class cloud_operations_:
    create_directory = create_directory_()
    write_file = write_file_()
    delete_item = delete_item_()
    read_file = read_file_()
    read_tree = read_tree_()

class Router:
    async def respond(self, view, payload, connection, sessionid):
        if view in self.mapping:
            response = self.mapping[view](Request(
                payload, connection, sessionid, self.cloud_operations
            ))
            if isinstance(response, Coroutine):
                return await response
            return response
        else:
            return "404 Not Found"

    def __init__(self, mapping:dict, models, private_key, database_schema_dir, database_path):
        self.cloud_operations = cloud_operations_()
        self.SESSION_USER_LOOKUP = SESSION_USER_LOOKUP
        self.generate_signed_sessionid = generate_signed_sessionid
        self.mapping = mapping
        self.models = models
        self.private_key = private_key
        self.database_schema_dir = database_schema_dir
        self.database_path = database_path
