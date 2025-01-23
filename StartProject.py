import sys, os
import pathlib
import secrets
import base64

def generate_security_key():
    """
    Generates a URL-safe base64-encoded cryptographically secure random key.
    
    The key is 32 bytes (256 bits) of random data, encoded without padding.
    Suitable for use as security keys, tokens, or other cryptographic purposes.
    """
    random_bytes = secrets.token_bytes(32)
    key = base64.urlsafe_b64encode(random_bytes).decode('utf-8').rstrip('=')
    
    return key

models_file_data = """from Fluxon.Database import Models
# your models go here...

class User(Models.AuthorizedUser):
    username = Models.CharField(max_length=100, unique=True)
    password = Models.CharField(max_length=200)
    email = Models.CharField(max_length=130)
    user_creation_date = Models.DateTimeField(auto_now_add=True)
"""

server_file_data = """from Fluxon.Endpoint import AsyncServer, run_server
import router

# Welcome to Fluxon!

server = run_server(AsyncServer(
    port=8080, secure=False,
    router=router.router
))
"""

router_file_data = lambda path: f"""from Fluxon.Routing import Router
import models, views

SERVER_SECURITY_KEY = "{generate_security_key()}"
DATABASE_SCHEMA_DIR = "{os.path.join(path, 'database_schema').replace('\\', '/')}"
DATABASE_PATH = "{os.path.join(path, 'database.sqlite3').replace('\\', '/')}"

router = Router(
    # routing setup
    mapping={"{"}
        # views mapping goes here...
    {"}"},
    # server setup
    private_key=SERVER_SECURITY_KEY,
    database_schema_dir=DATABASE_SCHEMA_DIR,
    database_path=DATABASE_PATH,
    models=models
)"""

class ProjectDirectoryNotFound(Exception):
    """raise when the provided directory don't exist"""

class UnknownServerSetup(Exception):
    """raise when the server setup is not natively supported"""

if len(sys.argv) == 3:
    # command extraction
    server = sys.argv[1]
    path = pathlib.Path(sys.argv[2])
    # project directory
    if path.exists():
        project_directory = path
    else:
        
        if path.parent.exists():
            path.mkdir()
            project_directory = path
        else:
            raise ProjectDirectoryNotFound(
                f"[Fluxon] unable to start your project | directoy ({path.parent}) not found"
            )
    if server == "AsyncServer":
        # server.py
        with open(os.path.join(project_directory, "server.py"), 'w') as server_file:
            server_file.write(server_file_data)
        # router.py
        with open(os.path.join(project_directory, "router.py"), 'w') as router_file:
            router_file.write(router_file_data(project_directory))
        # models.py
        with open(os.path.join(project_directory, "models.py"), 'w') as models_file:
            models_file.write(models_file_data)
        # views.py
        with open(os.path.join(project_directory, "views.py"), 'w') as views_file:
            views_file.write("# your views go here...")
        # database.sqlite3
        with open(os.path.join(project_directory, "database.sqlite3"), 'x') as views_file:
            pass
        # logs folder
        logs_directory = pathlib.Path(os.path.join(project_directory, "logs"))
        if not logs_directory.exists():
            logs_directory.mkdir()
        # database_schema folder
        database_schema_directory = pathlib.Path(os.path.join(project_directory, "database_schema"))
        if not database_schema_directory.exists():
            database_schema_directory.mkdir()
        print(f'[Fluxon] Your project is ready :)')
    else:
        raise UnknownServerSetup(
            f'[Fluxon] The server setup template "{server}" is not supported...'
        )
else:
    raise SyntaxError(
        "[Fluxon] Invalid command"
    )
