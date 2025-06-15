import os
import sys
import pathlib
import secrets
import base64

def generate_security_key(): # NOTE this function generates self-signed keys
    """
    Generates a URL-safe base64-encoded cryptographically secure random key.
    
    The key is 32 bytes (256 bits) of random data, encoded without padding.
    Suitable for use as security keys, tokens, or other cryptographic purposes.
    """
    random_bytes = secrets.token_bytes(86)
    key = base64.urlsafe_b64encode(random_bytes).decode('utf-8').rstrip('=')
    
    return key

models_file_data = """from Fluxon.Database import Models

# your models go here...

class User(Models.AuthenticatedUser):
    username = Models.CharField(max_length=100, unique=True)
    password = Models.CharField(max_length=200)
    email = Models.CharField(max_length=130, unique=True)
    user_creation_date = Models.DateTimeField(auto_now_add=True)
"""

cloud_authorization_model_data = """from Fluxon.Cloud.AuthorizationModels import RoleBasedAccessControl, Permissions, DefaultRole, AnonymousPermissions

# Write as many authorization models as you want
# You can Alternate between models in "router.py"

class CloudAuthorizationModel(RoleBasedAccessControl):
    # Roles and permissions definition goes here...
    class owner(RoleBasedAccessControl.Role):
        permissions=[
            Permissions.CREATE_FILE,
            Permissions.READ_FILE,
            Permissions.WRITE_FILE,
            Permissions.DELETE_FILE,
            Permissions.CREATE_SUB_DIRECTORY,
            Permissions.DELETE_SUB_DIRECTORY,
            Permissions.READ_TREE_DIRECTORY
        ]

    class collaborator(RoleBasedAccessControl.Role):
        permissions=[
            Permissions.READ_FILE,
            Permissions.WRITE_FILE,
            Permissions.READ_TREE_DIRECTORY,
            Permissions.CREATE_FILE
        ]

    class viewer(RoleBasedAccessControl.Role):
        permissions=[
            Permissions.READ_FILE,
            Permissions.READ_TREE_DIRECTORY
        ]

    # Set default role as viewer
    DefaultRole(viewer)
    AnonymousPermissions(
        permissions=[
            # Anonymous users get zero permissions
        ]
    )
"""

server_file_data = """from Fluxon.Endpoint import AsyncServer, run_server
import router

# Welcome to Fluxon!

run_server(
    AsyncServer(
        port=8080, secure=False,
        setup=router.setup
    )
)
"""

cloud_server_file_data = """from Fluxon.Endpoint import AsyncServer, CloudStorageServer, run_server
import router

# Welcome to Fluxon!

run_server(
    AsyncServer(
        port=8080, secure=False,
        setup=router.setup,

        # cloud storage setup
        cloud_storage=CloudStorageServer(
            port=8888, secure=False,
        )
    )
)
"""

router_file_data = lambda path: f"""import pathlib
from Fluxon.Routing import Setup
from Fluxon.Database.APIs import SQLiteDatabase
from Fluxon.Security import Secrets
import views, models

BASE_DIR = pathlib.Path("{path.as_posix()}")

DATABASE_SCHEMA_DIR = BASE_DIR / "database_schema"
LOGS_DIR = BASE_DIR / "logs"
SECRETS_DIR = BASE_DIR / "secrets"
DATABASE_PATH = BASE_DIR / "database.sqlite3"

setup = Setup(
    # Routing models & views
    mapping={{
        # Views mapping goes here...
        # You can use Fluxon.Routing.dynamic_views_loading as well
    }},
    models=models,

    # Server setup
    secrets=Secrets(SECRETS_DIR),
    database_schema_dir=DATABASE_SCHEMA_DIR,
    logs_dir=LOGS_DIR,
    database_path=DATABASE_PATH,
    database_api=SQLiteDatabase,
)
"""
cloud_router_file_data = lambda path: f"""import pathlib
from Fluxon.Routing import Setup
from Fluxon.Database.APIs import SQLiteDatabase
from Fluxon.Security import Secrets
from authorization_model import CloudAuthorizationModel
import views, models

BASE_DIR = pathlib.Path("{path.as_posix()}")

DATABASE_SCHEMA_DIR = BASE_DIR / "database_schema"
LOGS_DIR = BASE_DIR / "logs"
SECRETS_DIR = BASE_DIR / "secrets"
DATABASE_PATH = BASE_DIR / "database.sqlite3"
CLOUD_FOLDER = BASE_DIR / "cloud"

setup = Setup(
    # Routing models & views
    mapping={{
        # Views mapping goes here...
        # You can use Fluxon.Routing.dynamic_views_loading as well
    }},
    models=models,

    # Server setup
    secrets=Secrets(SECRETS_DIR),
    database_schema_dir=DATABASE_SCHEMA_DIR,
    logs_dir=LOGS_DIR,
    database_path=DATABASE_PATH,
    database_api=SQLiteDatabase,

    # Cloud storage setup
    cloud_folder=CLOUD_FOLDER,
    cloud_auth_model=CloudAuthorizationModel
)
"""

class ProjectDirectoryNotFound(Exception):
    """raise when the provided directory don't exist"""

class UnknownServerSetup(Exception):
    """raise when the server setup is not natively supported"""

def start_async_server(project_directory, cloud):
    # cloud
    if cloud:
        # authorization_model.py
        with open(project_directory / "authorization_model.py", 'w') as authorization_model_file:
            authorization_model_file.write(cloud_authorization_model_data)
        # cloud folder
        cloud_directory = project_directory / "cloud"
        if not cloud_directory.exists():
            cloud_directory.mkdir()
        # cloud/__init__.py
        with open(project_directory / "cloud" / "__init__.py", 'x'):
            pass
        # cloud/cloud_database.sqlite3
        with open(project_directory / "cloud" / "cloud_database.sqlite3", 'x'):
            pass
    server_file_ = (cloud_server_file_data if cloud else server_file_data)
    router_file_ = (cloud_router_file_data if cloud else router_file_data)
    # server.py
    with open(project_directory / "server.py", 'w') as server_file:
        server_file.write(server_file_)
    # router.py
    with open(project_directory / "router.py", 'w') as router_file:
        router_file.write(router_file_(project_directory))
    # models.py
    with open(project_directory / "models.py", 'w') as models_file:
        models_file.write(models_file_data)
    # views.py
    with open(project_directory / "views.py", 'w') as views_file:
        views_file.write("# your views go here...\n")
    # database.sqlite3
    with open(project_directory / "database.sqlite3", 'x'):
        pass
    # logs folder
    logs_directory = project_directory / "logs"
    if not logs_directory.exists():
        logs_directory.mkdir()
    # database_schema folder
    database_schema_directory = project_directory / "database_schema"
    if not database_schema_directory.exists():
        database_schema_directory.mkdir()
    # secrets folder
    secrets_directory = project_directory / "secrets"
    if not secrets_directory.exists():
        secrets_directory.mkdir()
    # secrets/server_private_key.pem
    with open(secrets_directory / "server_private_key.pem", 'w') as views_file:
        views_file.write(generate_security_key())
    print(f'[Fluxon] Your project is ready :)')

def execute():
    # command extraction
    server = sys.argv[1]
    if len(sys.argv) >= 3:
        path = pathlib.Path(sys.argv[-1])
    else:
        path = pathlib.Path(os.getcwd())
    # project directory
    if path.exists():
        project_directory = pathlib.Path(path.absolute())
    else:
        if path.parent.exists():
            path.mkdir()
            project_directory = pathlib.Path(path.absolute())
        else:
            raise ProjectDirectoryNotFound(
                f"[Fluxon] unable to start your project | directory ({path.parent}) not found"
            )
    if server == "AsyncServer":
        if '--cloud' in sys.argv:
            start_async_server(project_directory, cloud=True)
        else:
            start_async_server(project_directory, cloud=False)
    else:
        raise UnknownServerSetup(
            f'[Fluxon] The server setup template "{server}" is not recognized...'
        )

if __name__ == "__main__":
    try:
        execute()
    except Exception as e:
        print(f"[Fluxon] command not found \"{' '.join(sys.argv[1:])}\"")
        sys.exit(1)
