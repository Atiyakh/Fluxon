import uuid
import hmac
import hashlib
import base64

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

# abstract user class
class AuthenticatedUser:
    def __init__(
        self,
        id:int,
        username:str,
        email:str
    ):
        self.id = id
        self.username = username
        self.email = email
