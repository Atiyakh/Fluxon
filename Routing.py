from Fluxon.Cloud.AuthorizationModels import RoleBasedAccessControl
from Fluxon.Database.db_core_interface import DatabaseAPI
from Fluxon.Database.Models import Field
from Fluxon.Endpoint.auth_context import generate_signed_sessionid, AuthenticatedUser
from Fluxon.Security import Secrets
from collections.abc import Coroutine
from Fluxon.Database.Models import MODELS_INFO
import asyncio
import traceback
import pathlib
import inspect
import logging
import time
from datetime import datetime

SESSION_USER_LOOKUP = dict()
authorized_user_model: DatabaseAPI # Global variable to hold the authorized user model (hand-wavy I know but it works)

def dynamic_views_loading(module):
    functions = {name: obj for name, obj in inspect.getmembers(module) if inspect.isfunction(obj)}
    return functions

class Request:
    @staticmethod
    async def _analyze_user_query(query):
        if isinstance(query, Coroutine): # for async database APIs
            return Request._analyze_user_query(await query)
        elif isinstance(query, list):
            return AuthenticatedUser(*query[0])
        else:
            return False

    async def _find_user(self):
        try:
            if self.userid:
                self.user = await Request._analyze_user_query(
                    authorized_user_model.Check(
                        where=f"id = {self.userid}",
                        fetch=1,
                        columns=['id', 'username', 'email']
                    )
                )
            else:
                self.user = None
        except Exception as e:
            traceback.print_exc()
            raise RuntimeError(
                f"{e}: Invalid AuthenticatedUser Model | AuthenticatedUser model should have 'username' and 'email' fields, and the default 'id' AutoField as the primary key"
            ) from e

    async def _auth(self):
        if not self.connection.sessionid:
            if self.sessionid:
                if self.sessionid in self.connection.server.SESSION_CONNECTION_LOOKUP:
                    if self.connection in self.connection.server.SESSION_CONNECTION_LOOKUP[self.sessionid]:
                        self.connection.sessionid = self.sessionid
                    else:
                        self.connection.server.SESSION_CONNECTION_LOOKUP[self.sessionid].append(self.connection)
                        self.connection.sessionid = self.sessionid
                else:
                    self.sessionid = generate_signed_sessionid(self.connection, self.connection.server.router.private_key)
            else:
                self.sessionid = generate_signed_sessionid(self.connection, self.connection.server.router.private_key)
        if self.connection.sessionid in SESSION_USER_LOOKUP:
            self.connection.userid = SESSION_USER_LOOKUP[self.connection.sessionid]
            self.userid = SESSION_USER_LOOKUP[self.connection.sessionid]
        else:
            self.userid = None
            self.connection.userid = None
        # figure authenticated user
        await self._find_user()

    def login(self, id_):
        if self.connection.sessionid:
            session_removed = [session for session, user_id in SESSION_USER_LOOKUP.items() if user_id == id_]
            for session in session_removed:
                del SESSION_USER_LOOKUP[session]
            if type(id_) == int:
                SESSION_USER_LOOKUP[self.connection.sessionid] = id_
                return True
            else:
                raise TypeError(
                    f"AuthenticatedUserError: User id should be type int not {type(id_).__name__}"
                )
        else:
            print(" - Failed to login [INVALID SESSION]")
            return False

    def __init__(self, payload:dict, connection, sessionid:str):
        self.connection = connection
        self.server = connection.server
        self.timestamp = f"{datetime.now():%Y-%m-%d %H:%M:%S}.{datetime.now().microsecond // 1000:03}"
        self.payload = payload
        self.sessionid = sessionid
        print(f"{self.timestamp} - request received from {self.connection.peername[0]}:{self.connection.peername[1]}")

def analyze_roles(cloud_auth_model):
    subclasses = []
    for subclass_name in dir(cloud_auth_model):
        subclass = getattr(cloud_auth_model, subclass_name)
        if isinstance(subclass, type) and issubclass(subclass, RoleBasedAccessControl.Role) and subclass is not RoleBasedAccessControl.Role:
            subclasses.append(subclass)
    roles_names = [subclass.__name__ for subclass in subclasses]
    roles_permissions = [subclass.permissions for subclass in subclasses]
    roles_permissions_lookup = {role_name: permissions for role_name, permissions in zip(roles_names, roles_permissions)}
    return roles_names, roles_permissions_lookup

class InvalidSecrets(Exception):
    pass

class InvalidDatabaseAPI(Exception):
    pass

class Setup:
    async def respond(self, view, payload, connection, sessionid):
        if view in self.mapping:
            request = Request(
                payload, connection, sessionid
            )
            await request._auth()
            response = self.mapping[view](request)
            if isinstance(response, Coroutine):
                return await response
            return response
        else:
            return {"response": f"view '{view}' not found"}

    def get_server_private_key(self): # deprecated/incomplete
        try:
            with open(self.secrets.secrets_dir / "server_private_key.pem") as private_key_file:
                self.private_key = private_key_file.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"[ServerSetup] File 'server_private_key.pem' not found in directory {self.secrets.secrets_dir}")
        except PermissionError:
            raise PermissionError(f"[ServerSetup] Permission denied when accessing 'server_private_key.pem' in directory {self.secrets.secrets_dir}")
        except IOError as e:
            raise IOError(f"[ServerSetup] An I/O error occurred while trying to read 'server_private_key.pem': {e}")
        except Exception as e:
            raise Exception(f"[ServerSetup] An unexpected error occurred: {e}")

    def load_database_api(self):
        MODELS_INFO["database_api"] = self.database_api(
            self.database_path
        )

    def load_models(self):
        self.authorized_user_model = None
        for attrib_name in dir(self.models):
            attrib = getattr(self.models, attrib_name)
            if hasattr(attrib, '__base__') and attrib.__base__.__name__ in ("AuthenticatedUser", "Model"):
                # Check for authorized user model
                if attrib.__base__.__name__ == "AuthenticatedUser":
                    self.authorized_user_model = attrib
                    globals()['authorized_user_model'] = attrib 
                
                # Get Table/AsyncTable object from the DatabaseAPI
                if table := attrib.MODELS_INFO["database_api"].tables.get(attrib.__name__, False):
                    # Load CRUD functions
                    attrib.Check = table.Check
                    attrib.Insert = table.Insert
                    attrib.Update = table.Update
                    attrib.Delete = table.Delete
                    
                    # Load field names safely
                    missing_fields = []
                    for column_name in table.columns.keys():
                        if hasattr(attrib, column_name):
                            setattr(getattr(attrib, column_name), "column_name", column_name)
                        else:
                            if column_name == 'id': # automatically generated field if the developer didn't specify a primary key
                                id_field = Field() # abstract field object
                                id_field.column_name = column_name
                                setattr(attrib, column_name, id_field)
                            else:
                                missing_fields.append(f"{table.table_name}.{column_name}")
                    
                    if missing_fields:
                        self.logger.warn(f"Loading models error: Failed to load field names ({', '.join(missing_fields)}). ")
                        print(
                            f"- Failed to load field names ({', '.join(missing_fields)}). "
                            "Database API may not work as expected."
                        )
                else:
                    self.logger.warn(f"DatabaseSchemaMismatch: Model '{attrib.__name__}' is not properly defined in the database schema.")
                    print(
                        f"[DatabaseAPI] DatabaseSchemaMismatch: Model '{attrib.__name__}' is not properly defined in the database schema. "
                        "Ensure that the model is registered and the database schema is up to date. "
                        f"Current models schema includes [{', '.join(attrib.MODELS_INFO['database_api'].tables)}]"
                    )
    
    def initiate_logger(self):
        self.logs_path.mkdir(parents=True, exist_ok=True)
        # initializing logger
        logging.basicConfig(
            level=logging.INFO,
            format='%(levelname)s - %(asctime)s - %(message)s',
            handlers=[
                    logging.FileHandler(self.logs_path / f"{time.strftime('%Y-%m-%d', time.localtime())}.log"),
                ]
        )
        self.logger = logging.getLogger("main_logger")
    
    def load_secrets(self, secrets): # TODO
        pass

    def __init__(
            self,
            # mapping & models
            mapping:dict,
            models,
            # server setup
            secrets:Secrets,
            logs_dir:pathlib.Path,
            database_schema_dir:pathlib.Path,
            database_path:pathlib.Path,
            database_api:DatabaseAPI,
            # cloud setup args
            cloud_folder:pathlib.Path=None,
            cloud_auth_model:RoleBasedAccessControl=None
    ):
        # start an event loop and set it to the current thread
        self._event_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._event_loop)
        # set logger
        self.logs_path = logs_dir
        self.initiate_logger()
        # server setup
        self.SESSION_USER_LOOKUP = SESSION_USER_LOOKUP
        self.generate_signed_sessionid = generate_signed_sessionid
        if isinstance(secrets, Secrets):
            self.secrets = secrets
            self.load_secrets(secrets)
        else:
            self.logger.error(f"Invalid Secrets: Secrets should be a Fluxon.Security.Secrets object not {type(secrets).__name__}'")
            raise InvalidSecrets(
                f'[Security] Secrets should be a Fluxon.Security.Secrets object not {type(secrets).__name__}'
            )
        self.get_server_private_key() # NOTE this shit deprecated
        self.mapping = mapping
        # database
        self.database_schema_dir = database_schema_dir
        self.database_path = database_path
        if issubclass(database_api, DatabaseAPI):
            self.database_api = database_api
        else: raise InvalidDatabaseAPI(
            f"[Database] database_api argument should be a Fluxon.Database.db_core_interface.DatabaseAPI object not {type(database_api).__name__}"
        )
        # models handling
        self.models = models
        self.load_database_api()
        self.load_models()
        # cloud storage setup
        if cloud_auth_model and cloud_folder:
            self.cloud_folder = cloud_folder
            # authorization model setup
            self.cloud_auth_model = cloud_auth_model
            self.cloud_auth_model.MODEL_INFO["cloud_folder"] = cloud_folder
            self.cloud_auth_model.MODEL_INFO["database_path"] = database_path
            self.cloud_auth_model.MODEL_INFO["database_api"] = database_api
            self.cloud_auth_model.MODEL_INFO["roles_names"], self.cloud_auth_model.MODEL_INFO["roles_permissions_lookup"] = analyze_roles(self.cloud_auth_model)
            if self.authorized_user_model:
                self._event_loop.run_until_complete(self.cloud_auth_model._cloud_startup(self.cloud_auth_model, self.logger, self.authorized_user_model.__name__))
            else:
                self.logger.error("[CloudStorageServer-RBAC] AuthenticatedUser model not found. Authorization model needs an AuthenticatedUser model to run.")
                raise ModuleNotFoundError(
                    "[CloudStorageServer-RBAC] AuthenticatedUser model not found."
                )
