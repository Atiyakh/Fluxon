# What is Fluxon?
Fluxon is a lightweight general-purpose network engine written from scratch in Python. It offers secure communication, session handling, various server architectures and setups, and high-level database management making it an excellent choice for building server-side applications.

Fluxon combines the minimalist and flexible approach of Flask with Twisted's extensibility and scalability. It introduces a modular, flow-based architecture for seamless client-server communication and innovative features like reverse requests and built-in cloud integration. 

---

## Table of Contents
1. [Installation](#installation)
2. [Getting Started](#getting-started)
3. [Cloud Storage Setup](#setting-a-cloud-storage-server-optional-for-complex-server-structures)
4. [Features](#features)
5. [Why Fluxon](#why-choose-fluxon)
6. [License](#license)

---

## Installation

- **Just clone the repository to your local machine and you should be good to go**

```bash
git clone https://github.com/AtiyaKh/fluxon.git
```
*Watch out for dependencies at `requirements.txt`! Make sure they all installed as well.*

- **You can also use pip installation**

```bash
pip install Fluxon
```

---

## Getting Started

### Setting up The Server
**You can run this command `python -m Fluxon.StartProject AsyncServer path/to/project` and your project including `server.py` and `router.py` setup, models and views files, a logging directory for your server, database schema directory and a self-signed security key will all be automatically generated for you :)
These server templates will be expanded in the near future to include all the needed setups including a highly optimized HTTP server endpoint, FTP server endpoint, with cloud storage integration, and different database system integrations other than SQLite.** You can also set the server manually as follows, Fluxon is highly flexible with server setups.

Setting up the server is pretty simple. First you pick your favorite server from ```Fluxon.Endpoint```, let's say you happened to choose ```AsyncServer``` as your main Endpoint for your application (which is the only one available right now, more on the way tho)

write this in your ```server.py```
```python
from Fluxon.Endpoint import AsyncServer, run_server
import router

server = run_server(AsyncServer(
    port=8080, secure=False,
    router=router.router
))
```

```Fluxon.Endpoint.AsyncServer``` is a robust, flexible server infrastructure supporting asynchronous connections and reverse requests, making it ideal for most server setups.

You can also equip the server with a built-in highly-optimized cloud storage server, but it requires a complex setup and authorization mechanism. We'll talk about it in a second.

---

### Router Setup
The `Router` handles all incoming requests and maps them to appropriate views.

And this is ```router.py``` that we used in ```server.py```
```python
import pathlib
from Fluxon.Routing import Setup
from Fluxon.Database.Manipulations import AsyncSQLiteDatabase
from Fluxon.Security import Secrets
import views, models

BASE_DIR = pathlib.Path("automatically_generated/path/to/project")

SECRETS_DIR = BASE_DIR / "secrets"   # secrets directory contain automatically generated self-signed server key and certificate, which is convenient for testing and development
DATABASE_SCHEMA_DIR = BASE_DIR / "database_schema"
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
    database_path=DATABASE_PATH,
    database_api=AsyncSQLiteDatabase,
)
```

The `Setup` class centralizes routing, security, and database configurations. Define paths using `pathlib.Path` for critical directories like `SECRETS_DIR` and `DATABASE_SCHEMA_DIR` (contains SQL schema files). The `Setup` constructor accepts:  
- `mapping`: A dictionary linking URL routes to view handlers, you can also use `mapping=Fluxon.Routing.dynamic_views_loading(view)` to load all the functions in the `views` module to the router mapping (use it only when experimenting and testing different views; hardcode them when you're done).
- `models`: Models for database integration.
- `secrets`: A `Secrets` instance managing TLS certificates/keys and certificates
- `database_schema_dir`: Path to SQL schema migration files  
- `database_path`: Target file for the SQLite database *(other server-based databases will require access credentials instead)*
- `database_api`: Database engine adapter (e.g., `SQLiteDatabase`, `AsyncSQLiteDatabase`, etc)  

Initialize the setup object after importing project-specific `views` and `models`. Paths like `BASE_DIR` are auto-generated but can be overridden. For development, `Secrets` automatically creates self-signed certificates in `SECRETS_DIR`. Activate the configuration by passing the `setup` instance to your framework’s runtime entrypoint.  

---

### Database Management
#### Database Integration in Fluxon

Fluxon provides a seamless way to integrate a database with your application using an SQLite backend. The process is similar to Django’s ORM but with additional flexibility, allowing you to define models, manage schemas, and manipulate data easily. Here's a breakdown of the database workflow:

#### 1. **Defining Models**
Fluxon allows you to define database models in a Django-like fashion. You can create classes that represent your database tables, and these classes will automatically map to the corresponding SQL schema. Each class attribute corresponds to a column in the table.

For example:
```python
from Fluxon.Database import Models

class User(Models.AuthorizedUser):
    username = Models.CharField(max_length=100, unique=True)
    password = Models.CharField(max_length=200)
    email = Models.CharField(max_length=130)
    user_creation_date = Models.DateTimeField(auto_now_add=True)

class Teacher(Models.Model):
    user = Models.OneToOneField(to_table=User, primary_key=True)
    name = Models.CharField(max_length=100)
    department = Models.CharField(max_length=50)

class Course(Models.Model):
    course_name = Models.CharField(max_length=100)
    course_code = Models.CharField(max_length=10)
    teacher = Models.ForeignKey(to_table=Teacher, on_delete=Models.CASCADE)

class Student(Models.Model):
    user = Models.OneToOneField(to_table=User, primary_key=True)
    name = Models.CharField(max_length=100)
    birth_date = Models.DateField()
    courses = Models.ManyToManyField(to_table=Course, through='Enrollment')

class Enrollment(Models.Model):
    student = Models.ForeignKey(to_table=Student, on_delete=Models.CASCADE)
    course = Models.ForeignKey(to_table=Course, on_delete=Models.CASCADE)
    date_enrolled = Models.DateField(auto_now_add=True)
```

+ **You should use a ```Models.AuthorizedUser``` model only once!!**

#### 2. **Saving and Updating Database Schema**
Once the models are defined, you can save the schema, which Fluxon will translate into SQL queries. These queries will be stored as ```.sql``` files in your defined schema directory. This translation ensures that your models are reflected as actual SQL tables in your database.

saving schema is straightforward, type ```saveschema``` in the interactive server console, and the models you wrote will be automatically saved, loading that schema involved typing ```updateschema (schema number)``` in the server console. This should make alternating between schemas much easier.

#### 3. **Data Manipulations and Database Interactions**
Once the schema is set, Fluxon allows you to easily manipulate your data using ```Fluxon.Database.Manipulations.AsyncSqliteDatabase```, which is responsible for performing CRUD (Create, Read, Update, Delete) operations under the hood on your SQLite database. `AsyncSqliteDatabase` provides full I/O support and non-blocking flow. Asynchronous database handling requires writing asynchronous views, which is not a bad idea at all. This version uses connection pooling to optimize database performance and avoid blocking. It also manages concurrent sql writing operations without locking the database file.

- **Inserting Data:**

```python
await User.Insert({
    User.username: "username",
    User.password: "password"
})
```

And here is an example for ```SqliteDatabase``` implementation:

```python
User.Insert({
    User.username: "username",
    User.password: "password"
})
```

The ```Insert``` query should automatically return the id of the inserted row, returns ```False``` if it fails.

- **Updating Data:**

```python 
User.Update({User.email: "newemail@example.com"}, where[User.username == "filtering by username"])
```

And this is how an synchronous version looks like

```python 
User.Update({User.email: "newemail@example.com"}, where[User.username == "filtering by username"])
```

where statement accepts logical operators and ```&``` or ```|```

- **Querying Data:**
  
```python
users = await User.Check(where[User.username == "name"], fetch=number_of_results)
```
  
+ you can also drop the fetch argument to get a `True` or `False` result to validate a rows's existance in an if statement if you need.
+ set `fetch='*'` to grab all the results that fulfill the `where` statement.

- **Deleting Data:**

```python
await User.Delete(where[User.id == 3])
```
+ **`await User.Delete()` deletes everything, so be careful!**

Here is the thing tho, always add `await` before calling an asynchronous function, including all `AsyncSQLiteDatabase` interactions, that way you're telling python to alternate between tasks and eliminate any I/O-related blocking.

---

### Views
Views are functions that handle specific requests. It can send any python object over the network, meaning that the client will receive the exact thing the view function returns, you can literally send an AI model with this if you want.

Example signup view from ```views.py```:

```python
from Fluxon.Database.Manipulations import where
from Fluxon.Database.Validators import validate_email, validate_password, validate_username
from Fluxon.Security import Hash
from models import User

async def signup(request):
    # extract payload
    username = request.payload['username']
    email = request.payload['email']
    password = request.payload['password']
    # validation
    if not validate_username():
        return {'response': 'invalid username'}
    if not validate_email(email):
        return {'response': 'invalid email'}
    if not validate_password(password):
        return {'response': 'invalid password'}
    # insert user
    hashed_password = Hash.hash(password, algorithm=Hash.SHA512)
    user_id = await User.Insert(   # "Insert" returns the rowid of the inserted row
        username=username,
        email=email,
        password=hashed_password
    )
    # login user [binds the user id with the session/connetion/cloud server (if there was one ofc)]
    request.login(user_id)
    return {"response": "signed up successfully"}

async def login(request):
    # extract payload
    username = request.payload['username']
    password = request.payload['password']
    # check credentials
    hashed_password = Hash.hash(password, algorithm=Hash.SHA512)
    query = await User.Check(where[
        (User.username == username) & (User.password == hashed_password)
    ], fetch=1, columns=[User.id])
    if query:
        request.login(query[0][0])  # [0][0] -> [first result][fist column (the "id" column)]
        return {"response": "logged in successfully"}
    else:
        return {"response": "wrong username or password"}
```

The request passed to the view is a ```Fluxon.Routing.Request``` object that contains the client's peername, session id, user, the request payload, the connection object used by the server, and all the data you need. All requests passed are authenticated, you can authorize users (bind them to a user, which is supposed to be a Model.AuthorizedUser sub-class) using requests.login(user_id)

---

### Client Interaction
Fluxon provides high-level class ```ConnectionHandler``` for managing client-side communication.

#### Setting Up a Client

You can use this on the client side of your application, it manages sessions and socket connections automatically, and organizes the request send and receive process. It also keeps an open socket holding the same session id for reverse requests (from the server to the client) it allows for multiple requests for the same session at the same time, which is dope for a higher-level connection interface.

```python
from Fluxon.Connect import ConnectionHandler

conn = ConnectionHandler(host="127.0.0.1", port=8080)

# Example request
response = conn.send_request("signup", {"username": "test", "password": "test123"})
print(response)
```

---

### Running the Server

As we saw earlier, `run_server` from `Fluxon.Endpoint` is unironically responsible for running the server. Since we have already passed the server to `run_server` from the very beginning, you literally run `server.py` in order to run the server—how easy!

```bash
python server.py
```

The server will automatically run an interactive console so you can reach to the server directly from the console, like updating the database schema, or terminating, debugging, other low-level session or connection lookup and inside-server implementations, etc...

---

### Reverse Requests

A reverse request refers to a server-side request initiated by the server to trigger a **thread-safe** function on the client side, mapped to a specific function name. You can use `request.server.reverse_request` to send a reverse request during runtime. This allows for dynamic client-server interactions, particularly useful for real-time applications.
Reverse requests in Fluxon eliminate the need for messy and unstructured two-way communication implementations such as WebSockets. Mapping functions on the client side offers a high-level abstraction that simplifies bidirectional communication.

Below is an example of a real-time chat server utilizing reverse requests to send messages to clients:

This is the view for sending a message and making a reverse request. Write this function in the server-side `views.py` and don't forget to map it in `router.py`!
```python
async def send_message(request):
    if request.userid:
        sender = (await User.Check(where[User.id == request.userid], fetch=1, columns=[User.username]))[0][0]
        query = await User.Check(where[User.username == request.payload["to"]], fetch=1, columns=["id"])
        if query:
            id = query[0][0]
            # reverse_request takes the userid of the requested user, the name of the function triggered, and the payload passed to that function.
            # it returns a boolean of whether the server was able to send the request.
            status = await request.server.reverse_request(id, "receive_message", {
                "from": sender,
                "message": request.payload["message"]
            })
            if status: return "sent!"
            else: # if the client is not online, do something else, maybe saving it in the database or something
                return f"{request.payload['to']} is offline!"
    else: return "login needed"
```

And here is the new client connection setup
```python
# this function will be called whenever a "receive_message" reverse request is called
def receive_message(payload):
    print(f"{payload['from']}: {payload['message']}")

conn = ConnectionHandler(host=gethostbyname(gethostname()), port=8080)
# map different reverse requests with functions here
conn.reverse_request_mapping({
    "receive_message": receive_message,
})

# logging in
conn.send_request("login",{
    "username": "Mike",
    "password": "M@123abc"
})

# request for sending a message
response = conn.send_request("send_message",{
    "to": "John",
    "message": "Hello, John!"
})

print(response)
# prints either "sent!" or "John is offline!"
```

+ Just remember that reverse request functions should be always thread-safe! (I will make some quick cross-thread communication solutions for common non-thread-safe function cases soon)
+ In multi-threaded applications, when the `ConnectionHandler` needs to call non-thread-safe reverse view functions in the main thread (such as a function that updates GUI elements based on server inputs from the reverse request, like getting a notification or receiving a message or whatever), directly invoking them can cause issues. To handle this, use a worker thread that places function calls into a thread-safe queue, which the main thread periodically checks and processes. This ensures that non-thread-safe operations are executed in the main thread without causing threading conflicts.

---

## Setting a Cloud Storage Server (optional; for complex server structures)

**Run this command `python -m Fluxon.StartProject AsyncServer --cloud path/to/project` for a fully-integrated RBAC cloud server.**

That's your new ```server.py``` with a `CloudStorageServer` integration (I will elaborate more on different server setups and integrations when I make other custom endpoints):

```python
from Fluxon.Endpoint import AsyncServer, CloudStorageServer, run_server
import router

run_server(AsyncServer(
    port=8080, secure=False,
    setup=router.setup,

    # cloud storage setup
    cloud_storage=CloudStorageServer(
        port=8888, secure=False,
    )
))
```

And here's the code for ```router.py```

```python
import pathlib
from Fluxon.Routing import Setup
from Fluxon.Database.Manipulations import AsyncSQLiteDatabase
from Fluxon.Security import Secrets
from authentication_model import CloudAuthenticationModel
import views, models

BASE_DIR = pathlib.Path("automatically_generated/path/to/project")

SECRETS_DIR = BASE_DIR / "secrets"
DATABASE_SCHEMA_DIR = BASE_DIR / "database_schema"
DATABASE_PATH = BASE_DIR / "database.sqlite3"
CLOUD_FOLDER = BASE_DIR / "cloud"

setup = Setup(
    # Routing models & views
    mapping={
        # Views mapping goes here...
        # You can use Fluxon.Routing.dynamic_views_loading as well
    },
    models=models,

    # Server setup
    secrets=Secrets(SECRETS_DIR),
    database_schema_dir=DATABASE_SCHEMA_DIR,
    database_path=DATABASE_PATH,
    database_api=AsyncSQLiteDatabase,

    # Cloud storage setup
    cloud_folder=CLOUD_FOLDER,
    cloud_auth_model=CloudAuthenticationModel
)
```

---

Write your authentication models in `authentication_model.py`, you will find an automatically generated one that looks like so:

```python
from Fluxon.Cloud.AuthorizationModels import RoleBasedAccessControl, Permissions, DefaultRole, AnonymousPermissions

# Write as many authentication models as you want
# You can alternate between models in "router.py"

class CloudAuthenticationModel(RoleBasedAccessControl):
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
```

The `CloudAuthenticationModel` implements a **role-based access control (RBAC)** system. To define roles, subclass `RoleBasedAccessControl` and declare nested classes inheriting from `RoleBasedAccessControl.Role`. Each role specifies a `permissions` list using the `Permissions` enum (e.g., `Permissions.READ_FILE`). Available permissions include:  
- `CREATE_FILE`
- `READ_FILE`
- `WRITE_FILE`
- `DELETE_FILE`
- `CREATE_SUB_DIRECTORY`
- `DELETE_SUB_DIRECTORY`
- `READ_TREE_DIRECTORY`
- `ASSIGN_ROLES` *allows the role with this permission to assign roles to other users to file/folder*

+ **Subdirectories and files inherit parent roles if children roles were not specified**
+ **Assigned roles for subdirectories and files overrides parents permissions, untill this sub-role is removed**

Assign a default role with `DefaultRole(YourRoleClass)` to handle unauthenticated users with explicit roles. Configure anonymous access via `AnonymousPermissions(permissions=[...])`—which by default (in this example), has no permissions at all. Integrate this model in `router.py` by importing and simply passing it in the routing configuration `cloud_auth_model` (take a look at the previous `router.py` example for 
more context).

---

You can manage roles and permissions directly from `views.py`, here are two simple example to views/cloud interactions and dynamics:
```python
from authentication_model import CloudAuthenticationModel
from models import User
from Fluxon.Database.Manipulations import where

async def assign_user_as_viewer(request):
    if request.user:
        # payload
        user_to_assign = request.payload['user_to_assign']
        authorized_cloud_relative_path = request.payload['path']
        # authorization
        if CloudAuthenticationModel.can_authorize_path(    # if the user role on this path does not have a `Permissions.ASSIGN_ROLES` permission, `can_authorize_path` will return `False`
            path=authorized_cloud_relative_path, user=request.user
        ):
            # assign role
            if query := await User.Check(where[User.username == user_to_assign], fetch=1, columns=[User.id]):
                user_id = query[0][0]   # -> [first result][first column (the "id" basically)]
                status = CloudAuthenticationModel.assign_user_role(
                    role=CloudAuthenticationModel.viewer,
                    user_id=user_id,   # | you can use `user`, `user_id`, and 'username' to indentify users in cloud interactions
                    path=authorized_cloud_relative_path
                )
                return status
            else:
                return {"response": f"user {user_to_assign} not found"}
        else:
            return {"response": f"you can't authorize users to this path ({authorized_cloud_relative_path})"}
    else:
        return {"response": "login needed"}

async def assign_me_as_owner(request):
    if request.user:
        cloud_relative_path = request.payload['path']
        # In this example, 'owner' role is granted to the creator of the file only
        if CloudAuthenticationModel.filesystem.path(cloud_relative_path).creator.id == request.user.id:
            status = CloudAuthenticationModel.assign_user_role(CloudAuthenticationModel.owner, user=request.user)
            return status
        else:
            return {"response": "you didn't create this file, so you will not be assigned as the 'owner'"}
    else:
        return {"response": "login needed"}
```
---
***The same models we worked with in the beginning will be automatically connection with the RBAC models like in this diagram***
![]([https://github.com/Atiyakh/Fluxon/blob/main/diagrams/cloud_integrated_models.png](https://raw.githubusercontent.com/Atiyakh/Fluxon/refs/heads/main/diagrams/cloud_integrated_models.png))
---

And here is how the client interacts with them:

```python
from Fluxon.Connect import ConnectionHandler, CloudStorageConnector

# starting the connection
server_connection = ConnectionHandler(host='localhost', port=8080)
cloud_connection = CloudStorageConnector(host='localhost', port=8888)

# logging in
server_connection.send_request("login", {
    'username': "Jane",
    'password': "Jane123@abc"
})

# creating a directory in the cloud root dir
cloud_response = cloud_connection.create_directory(relative_path="/janes_dir")

# claim ownership
response = server_connection.send_request("assign_me_as_owner", {'path': "/janes_dir"})

cloud_response = cloud_connection.create_file(relative_path="/janes_dir/some_file.txt") # no need to claim ownership, the user inherits it from the parent directory `/janes_dir`
cloud_response = cloud_connection.write_file(relative_path="/janes_dir/some_file.txt", data=b"some text... 123, some more text @#$abc") # no need to claim ownership, the user inherits it from the parent directory `/janes_dir`

# assign Mike as a viewer to `/janes_dir/some_file.txt`. she can since she's assigned as 'owner' to the file, and the role 'owner' has `ASSIGN_ROLE` in its permissions 
response = server_connection.send_request("assign_user_as_viewer", {'user_to_assign': "Mike", 'path': "/janes_dir"})
```

---

## Features

- **Independent Server Architecture:** Fluxon is not tied to browser-based interaction, making it ideal for real-time and unconventional server setups.
- **Simplified Reverse Requests:** Easily implement bidirectional communication without the complexity of WebSockets or low-level networking protocols.
- **Flexible Routing:** Intuitive mapping of request paths to view functions with support for asynchronous workflows, enabling seamless request handling.
- **Integrated Cloud Storage System:** Built-in cloud storage support acts like a media system with unparalleled flexibility and server-side authorization.
- **Database Integration:** Use a Django-inspired ORM to define models and manage schemas with SQLite for streamlined database operations.
- **Secure Sessions:** Session-based authentication secured with private keys for robust communication.
- **Python Object Serialization:** Effortlessly send and receive complex Python objects using `pickle`.
- **Session Management:** Manage persistent client-server connections with advanced session handling.
- **Asynchronous Support:** Optimized performance with async-ready components for servers, databases, and views. Fluxon native endpoints like `AsyncServer` significantly outperforms Flask and Django due to its end-to-end asynchronous architecture. (see [benchmark test results](https://github.com/Atiyakh/Fluxon/tree/main/benchmarks))

#### **Here are some benchmark results for managing 400 concurrent requests of 50 KB each:**
| Framework    | Total Time (400 requests) | Average Response Time |
|--------------|---------------------------|-----------------------|
| **Fluxon**   | 0.83s                     | 2.1ms                 |
| **Django**   | 1.56s                     | 3.9ms                 |
| **FastAPI**  | 0.70s                     | 1.8ms                 |
| **Flask**    | 1.42s                     | 3.5ms                 |

##### Fluxon ranks second in speed for server endpoints, following FastAPI.
---

## Why Choose Fluxon?

Fluxon stands out from traditional frameworks like Django, Flask, or Twisted by offering a unique blend of flexibility, simplicity, and power for unconventional server architectures. Here's what makes Fluxon special:

### 1. Independent of Browsers
- Unlike frameworks like Django, Fluxon is not tied to browser-based interaction.
- This makes it ideal for applications requiring real-time or non-browser-based clients.

### 2. Simplified Reverse Requests
- Reverse requests are intuitive and easy to implement, eliminating the complexity of WebSockets or other low-level networking protocols.
- Developers with limited networking expertise can still implement robust, real-time, bidirectional communication.

### 3. Flexible Request Handling
- Fluxon allows highly customizable request handling with minimal effort.
- Define routes, map them to views, and integrate them with asynchronous workflows to fit any server structure.

### 4. Integrated Cloud Storage System
- Fluxon features a built-in cloud storage system, offering:
  - Server-side flexibility with robust authorization mechanisms.
  - Client-side simplicity for seamless integration.
- No need for third-party storage systems—Fluxon’s solution is as easy to use as Django’s media system, but far more customizable.

### 5. Perfect for Unconventional Server Architectures
- Fluxon thrives in environments where traditional frameworks fall short.
- Its modular design makes setting up servers, routers, models, views, and cloud storage straightforward and adaptable.
- Ideal for research-oriented, experimental, or highly customized applications.

---

## License
This project is licensed under the MIT License.
