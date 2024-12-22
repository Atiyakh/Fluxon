import uuid
import hmac
import hashlib
import base64

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
                    self.sessionid = generate_signed_sessionid(self.connection, self.private_key)
            else: # the dude aint got nothin; bake him a sessionid
                self.sessionid = generate_signed_sessionid(self.connection, self.private_key)
        if self.connection.sessionid in SESSION_USER_LOOKUP:
            self.connection.userid = SESSION_USER_LOOKUP[self.connection.sessionid]
            self.userid = SESSION_USER_LOOKUP[self.connection.sessionid]
        else:
            self.userid = None
            self.connection.userid = None

    def login(self, id_):
        if self.connection.sessionid:
            SESSION_USER_LOOKUP[self.connection.sessionid] = id_
        else:
            print(" - Faild to login [INVALID SESSION]")

    def __init__(self, payload, connection, sessionid):
        self.connection = connection
        self.payload = payload
        self.sessionid = sessionid
        self.__auth()

class Router:
    def respond(self, view, payload, connection, sessionid):
        if view in self.mapping:
            return self.mapping[view](Request(
                payload, connection, sessionid
            ))
        else:
            return "404 Not Found"

    def __init__(self, mapping:dict, models, private_key, database_schema_dir, database_path):
        self.SESSION_USER_LOOKUP = SESSION_USER_LOOKUP
        self.generate_signed_sessionid = generate_signed_sessionid
        self.mapping = mapping
        self.models = models
        self.private_key = private_key
        self.database_schema_dir = database_schema_dir
        self.database_path = database_path
