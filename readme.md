# Fluxon

## 🚧 This project is currently in alpha. 🚧

It is still under active development and not ready for production use.
The structure, features, and APIs may change significantly without notice.

Please do not clone, fork, or use this project in production just yet — unless you're contributing directly to development.

A stable release will be announced once the project matures.

---

Fluxon is a lightweight Python-based general-purpose network engine. It offers secure communication, session handling, various server architectures and setups, and high-level database management making it an excellent choice for building server-side applications.

I built Fluxon because I wanted a framework that combined Flask’s simplicity with Twisted’s power—but without the boilerplate. Along the way, I stumbled into designing a custom RPC system, a role-based cloud storage engine, and an async ORM. I love CS, and I absolutely love to carve things up and see how they work on the inside (I have done unspeakable things to Django's docs about ORM and CURD operations to pull this off), so here we are, no more magic boxes, no more libraries and dependencies. I built that from scratch because I was curious, and because I wanted to learn. I introduce FLUXON 🎉

---

## Table of Contents

1. [Installation](#installation)
2. [Getting Started](#getting-started)
3. [Filesystem Setup](#setting-a-cloud-storage-server-optional-for-complex-server-structures)
4. [Features](#features)
5. [Why Fluxon](#why-choose-fluxon)
6. [License](#license)

---

## Installation

- **Clone the repository to your local machine and you’re ready to go.**

```bash
git clone https://github.com/AtiyaKh/fluxon.git
```

---

## Getting Started

Here’s how this piece of software works:

### Setting up The Server

Start by choosing a server type from `Fluxon.Endpoint` module. For this example, we’ll use `AsyncServer` as the main endpoint for the application. (Additional protocols like `FTP`, `HTTP`, and `SMTP`, along with their asynchronous versions, will be available later today.)

To create a new project using `AsyncServer`, run the following command in your terminal _(Omit the path if you're already in your project directory)_

```bash
python -m Fluxon.StartProject AsyncServer path/to/new_project
```

Open the generated `server.py` file. This file defines your server's endpoint. This `run_server` function accepts any server endpoint as its first argument. It blocks execution while the server is running, launches an interactive console in the background, and shuts everything down gracefully when you press `Ctrl+C`.

```python
from Fluxon.Endpoint import AsyncServer, run_server
import router

# Welcome to Fluxon!

run_server(
    AsyncServer(
        port=8080, secure=False,
        setup=router.setup
    )
)
```

---

### Running the Server

```bash
python server.py
```

The server will automatically run an interactive console so you can access the server inner workings directly from there, like saving or updating the database schema, terminating or debugging sessions, or other low-level sessions and connections lookup, or exploring other low-level server internals.

---

`Fluxon.Endpoint.AsyncServer` is a robust, flexible server infrastructure supporting asynchronous connections and reverse requests, making it ideal for most server setups.

You can also equip the server with a built-in highly-optimized filesystem with role-based access control, but it requires a complex setup and authorization mechanism. We'll talk about it in a second.

---

### Router Setup

`Setup` from the `Fluxon.Routing` module handles all incoming requests and routes them to appropriate views under the hood. It also manages server components and configurations for database, logging, security keys, and views mapping.

Go ahead and open `router.py` (the one we imported in `server.py` right above), you'll find the following code already generated for you.

```python
from Fluxon.Routing import Router
import models, views

DATABASE_SCHEMA_DIR = BASE_DIR / "database_schema"
LOGS_DIR = BASE_DIR / "logs"
SECRETS_DIR = BASE_DIR / "secrets"
DATABASE_PATH = BASE_DIR / "database.sqlite3"

setup = Setup(
    # routing models & views
    mapping={
        # views mapping goes here...
        # you can use Fluxon.Routing.dynamic_views_loading as well
    },
    models=models,

    # server setup
    secrets=Secrets(SECRETS_DIR),
    database_schema_dir=DATABASE_SCHEMA_DIR,
    logs_dir=LOGS_DIR,
    database_path=DATABASE_PATH,
    database_api=SQLiteDatabase,
)
```

---

### Database Management

#### Database Integration in Fluxon

Fluxon provides a seamless way to integrate a database with your application using an `SQLite` backend. The process is similar to Django’s ORM but with additional flexibility, allowing you to define models, manage schemas, and manipulate data easily. Here's a breakdown of the database workflow:

##### 1. **Defining Models**

Fluxon allows you to define database models in a Django-like fashion. You can create classes that represent your database tables, and these classes will automatically map to the corresponding SQL schema. Each class attribute corresponds to a column in the table.

For example:

```python
from Fluxon.Database import Models

class User(Models.AuthenticatedUser):
    username = Models.CharField(max_length=100, unique=True)
    password = Models.CharField(max_length=200)
    email = Models.CharField(max_length=130, unique=True)
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
---
<p align="center">
  <img src="https://raw.githubusercontent.com/Atiyakh/Fluxon/refs/heads/main/diagrams/school_models_example.png" alt="Example: School Models Diagram">
</p>

---

+ **You should use a `Models.AuthenticatedUser` model only once!**

##### 2. **Saving and Updating Database Schema**

Once your models are defined in `models.py`, you can save your schema to the designated database schema directory, which Fluxon will translate into SQL queries. These queries will be stored in a `.sql` file, with a serial number attached to the file name. This translation ensures that your models are reflected as actual SQL tables in your database. These files follow this format strictly (`schema_xxxxx.sql`), for this number attached to it (`xxxxx`) will be referenced in all database schema-related interactions to differentiate between them, like we mentioned in the `updateschema <number>` command. This will help you can alternate between different versions and schemas.

> 🚨 **BE CAREFUL!** Those SQL-defined tables are DBMS-specific, It will be inferred from your `router.setup.database_api` (e.g., `Setup(...database_api=SQLiteDatabase, ...`). If you're using an `SQLite` database adapter, like `SQLiteDatabase`, your tables will be stored as `SQLite` tables. Use a `MySQL` adapter, and you will have them in `MySQL` syntax instead.

Saving schema is straightforward, type `saveschema` in the interactive server console, and the models you wrote will be automatically saved, loading that schema involves typing the command `updateschema <schema_number (or leave it blank to use the latest schema)>` in the server console.

##### 3. **CRUD Database Operations**

Once the schema is set, Fluxon allows you to easily store your data using `Fluxon.Database.APIs.SQLiteDatabase`, which is responsible for performing CRUD (Create, Read, Update, Delete) operations on your SQLite database.

```python
from Fluxon.Database.APIs import SQLiteDatabase

db = SQLiteDatabase("path/to/database_file")
```

~~Or you can use `AsyncSQLiteDatabase` for full I/O support and non-blocking flow. Asynchronous database handling requires writing asynchronous views, which is not a bad idea at all. This version uses connection pooling to optimize database performance and avoid blocking. It also manages concurrent sql writing operations without locking the database file.~~

> 🚨 **`AsyncSQLiteDatabase`** is **deprecated** and should be avoided. It’s prone to crashing under heavy load or dense connections due to `SQLite`’s limitation in handling multiple parallel connections. While it uses connection pooling, `SQLite`’s single-threaded nature makes it unreliable for concurrent read/write operations. For better performance and stability, consider using a more suitable database adapter like the `AsyncMySQLDatabase` adapter from the `Fluxon.Database.APIs` module.

- **Inserting Data:**

```python
from models import User

User.Insert({
    User.username: "Mike",
    User.password: "Mike@123abc"
})
```

And here is an example for an asynchronous database adapter row insertion

```python
await User.Insert(
    # you can also insert values as keyword arguments
    username="Mike",
    password="Mike@123abc"
)
```

These `Insert` queries should automatically return the `id` of the inserted row, returns `False` if it fails (e.g., table constraint violation).

- **Updating Data:**

```python 
from Fluxon.Database.Query import where
User.Update({
        User.email: "new_email_for_jake@mail.com"
    },
    where[User.username == "Jack"]
)
```

And this is how an async version would look like, just remember to write async views as well

```python 
await User.Update({
        User.email: "new_email_for_jake@mail.com"
    },
    where[User.username == "Jack"] # ← where clauses accepts logical operators (&) and (|)
)
```

- **Querying Data:**
  
```python
users = User.Check(where[User.username == "name"], fetch=number_of_results_needed)
```

```python
users = await User.Check(where[User.username == "name"], fetch=number_of_results_needed)
```
  
you can also drop the fetch argument to get all the data filtered using `where` statement

- **Deleting Data:**
  
```python
User.Delete(where[User.id == 3])
# drop the where clause, and you'll wipe the whole table
```

`User.Delete()` clears the `User` table with no going back 😬

```python
# asynchronous equivalent
await User.Delete(where[User.id == 3])
```

---

#### **We mentioned *asynchronous* functions a handful of times... but what are they exactly? _(Skip this if you know asynchronous programming.)_**

If you're not very familiar with Python’s `async/await` syntax, don't worry! we won’t go into too much detail. The main idea is simple:

- Add `await` before calling an asynchronous function. This tells Python to yield control while the task waits on something (like I/O), so the program can work on other tasks in the meantime.
- Any function that uses `await` must itself be marked as `async`.

```python
# Here is an example, let me explain
# 1. Add the word `async` just before the function declaration
async def AsynchronousFunction(): # ← We call those coroutines! (coroutines are scheduled task)
    # 2. add `await` before calling an async function
    result = await AnotherAsynchronousFunction()
    # ↑ `await` sends coroutines (tasks) to the event loop, where they will be executed in the right time 
# 3. And we're done!
```

#### **🤔 But what is this? like *Why*?**

Asynchronous programming with `async/await` utilizes an event-driven model to execute tasks in a **non-blocking** manner, enabling the program to manage multiple tasks **concurrently** on a single thread. Rather than waiting for tasks, especially **I/O-bound** ones (like database writes or API calls), to complete, the program yields control back to the *event loop* (the program's tasks clerk basically). The event loop decides which tasks run and which wait, based on dependencies or missing components of other *outsider tasks*. This approach saves time in I/O-heavy workflows, such as those found in servers or databases, by interleaving operations and **reducing idle time**. It allows the system to remain responsive while efficiently utilizing resources. Essentially, it **provides concurrency without parallelism**, enabling progress on multiple tasks without the need for multiple threads or processes.

Now that we got that out of the way, let's get back on the road!

---

### Views

These are typical python functions (can be either sync or async functions) that handle specific requests, mapped to specific names on the `router.py`'s end. They expect the conventional `request` argument, which fills it in with both the *context* and the *content* of the request. They also return an object (response) that will be serialized, compressed, and sent over the network to the far host (the client).

You will typically focus on the logic and flow of the code, you may need to interact with the database, read files, manage filesystem interactions, authentication and authorization too, or take any sort of server-side action. this makes them one of the most important, powerful, and moving part of your project (I'm not even glazing), and they should be taken seriously.

Example signup view from `views.py`:

```python
def signup(request):
    User.Insert(request.payload) # 🚨 Do not dump data into the database like that! we will be using validators ☝️🤓
    return {"Response": "Signed up successfully!"}
```

And here is an asynchronous version of the same function (optimized for I/O systems, we talked about that)

```python
async def signup(request):
    """asynchronous view functions introduce way less blocking than synchronous ones"""
    await User.Insert(request.payload)
    return {"status": "200", "message": "Signed up successfully"}
```

The request passed to the view is a ```Fluxon.Routing.Request``` object that contains the client's `peername` (client's ip and port), `sessionid`, `AuthenticatedUser` object (you can use it to validate users and pull user's data), the request `payload` (whatever the client sends with the request), the `connection` object (that's a low-level object used by the server to hold sockets and coordinate connections, associate them with sessions and users, and send/receive raw data), and all the data you need. All requests passed are authenticated. You can authenticate users (bind them to a user, which is supposed to be a Model.AuthenticatedUser sub-class) using `requests.login(user_id)`, we will see how it works in a minute.

Here is a more *typical* example

```python
from Fluxon.Database.Query import where
from Fluxon.Database.Validators import validate_email, validate_password, validate_username
from Fluxon.Security import Hash
from models import User

async def signup(request):
    # extract payload
    username = request.payload.get('username')
    email = request.payload.get('email')
    password = request.payload.get('password')
    # validation
    # 📜 Rule no. 1: Never trust the client with anything, always check for everything!
    if not validate_username(username):
        return {'Response': 'Invalid username'}
    if not validate_email(email):
        return {'Response': 'Invalid email'}
    if not validate_password(password):
        return {'Response': 'Invalid password'}
    # insert user
    hashed_password = Hash.hash(password, algorithm=Hash.SHA512)
    if user_id := await User.Insert(   # "Insert" returns the `rowid` of the inserted row
        username=username,
        email=email,
        password=hashed_password
    ):
        # login user [binds the user id with the session/connection/cloud server (if there was one ofc)]
        request.login(user_id)
        return {"Response": "Signed up successfully!"}
    else:
        return {"Response": "Signed up Failed :("}

async def login(request):
    # extract payload
    username = request.payload.get('username')
    password = request.payload.get('password')
    # check credentials
    hashed_password = Hash.hash(password, algorithm=Hash.SHA512)
    user_id_query = await User.Check(where[
        (User.username == username) & (User.password == hashed_password)
    ], fetch=1, columns=[User.id])
    if user_id_query:
        request.login(user_id_query[0][0])  # [0][0] → [first result][first column (the "id" column)]
        return {"response": "logged in successfully"}
    else:
        return {"response": "wrong username or password"}
```

---

### Client Interactions

Fluxon provides high-level class `ConnectionInterface` for managing client-side communication.

#### Setting Up a Client

You can use this on the client side of your application, it manages sessions and socket connections automatically, and organizes the request send and receive process. It also keeps an open socket holding the same session id for reverse requests (from the server to the client) it allows for multiple requests for the same session at the same time, is excellent for high-level client-server interactions.

> ⚠️ `ConnectionInterface` manages its own persistent socket connections, avoid re-initializing it on every request unless needed. Each `ConnectionInterface` instance carry a distinct session in the server side. They can share the same session if needed _(not recommended)_

```python
from Fluxon.Connect import ConnectionInterface

connection = ConnectionInterface(host="localhost", port=8080)

# Example request
response = connection.send_request(
    view_name="signup",
    payload={
        "username": "Emma",
        "password": "Emm@'s_password123"
    }
)
print(response)
```

---

### Reverse Requests _(RPC bidirectional-like design)_

A reverse request refers to a server-side request initiated by the server to trigger a function on the client side, mapped to a specific function name. You can use `request.server.reverse_request` to send a reverse request during runtime. This allows for dynamic client-server interactions, particularly useful for real-time applications.

Reverse requests in Fluxon eliminate the need for messy and unstructured two-way communication implementations such as WebSockets. Mapping functions on the client side offers a high-level abstraction that simplifies bidirectional communication.

Below is an example of a real-time chat server utilizing reverse requests to send messages to clients:

This is the view for sending a message and making a reverse request. Write this function in the server-side `views.py` and don't forget to map it in `router.py`!

```python
def create_user(request):
    username = request.payload.get('username')
    password = request.payload.get('password')
    email = request.payload.get('email')
    # validation
    if not validate_username(username):
        return {'response': 'invalid username'}
    if not validate_email(email):
        return {'response': 'invalid email'}
    if not validate_password(password):
        return {'response': 'invalid password'}
    # insert user
    hashed_password = Hash.hash(password, algorithm=Hash.SHA512)
    if user_id := User.Insert(
        username=username,
        email=email,
        password=hashed_password
    ):
        request.login(user_id)
        return {"response": "signed up successfully"}
    else:
        return {"response": "username or email already exists"}

def login(request):
    username = request.payload['username']
    password = request.payload['password']
    # check credentials
    hashed_password = Hash.hash(password, algorithm=Hash.SHA512)
    query = User.Check(where[
        (User.username == username) & (User.password == hashed_password)
    ], fetch=1, columns=[User.id])
    if query:
        request.login(query[0][0])
        return {"response": "logged in successfully"}
    else:
        return {"response": "wrong username or password"}

async def send_message(request):
    # extract data
    receiver = request.payload.get('receiver')
    message = request.payload.get('message')

    if request.user: # ← check if the request sender is a logged in user with an id
        sender = request.user.username
        receiver_id_query = await User.Check(where[User.username == receiver], fetch=1, columns=["id"]) # look up the receiver's user id
        if receiver_id_query:
            receiver_id = receiver_id_query[0][0]
            # reverse_request takes the user id of the requested user, the name of the target reverse function, and the payload passed to that function.
            # it returns a boolean of whether the server was able to "reverse request" the far client or not.
            status = await request.server.reverse_request(receiver_id, "receive_message", {
                "sender": sender,
                "message": message
            })
            if status:
                return "sent!"
            else: # if the client is not online, do something else, maybe saving it in the database or something
                return f"{receiver} is offline!"
    else: # refuse if the sender is not logged in
        return "login needed"
```

And here's the chatroom client file

```python
from Fluxon.Connect import ConnectionInterface

def receive_message(sender, message):
    print(f"[{sender}] {message}")

connection = ConnectionInterface(host="localhost", port=8080)
connection.reverse_request_mapping(
    {
        "receive_message": receive_message
    }
)

def create_user(username, password, email):
    return connection.send_request("create_user", {
        'username': username,
        'password': password,
        'email': email
    })

def login(username, password):
    return connection.send_request("login", {
        'username': username,
        'password': password
    })

def send_message(message, receiver):
    return connection.send_request("send_message", {
        'message': message,
        'receiver': receiver
    })

# simple user interaction like signing in, logging out, sending messages,...
if __name__ == "__main__":
    print("Enter command (create_user, login, send_message, exit):\n\n")
    while True:
        command = input().strip()
        if command == "exit":
            break
        elif command == "create_user":
            username = input("Username: ")
            password = input("Password: ")
            email = input("Email: ")
            print(create_user(username, password, email))
        elif command == "login":
            username = input("Username: ")
            password = input("Password: ")
            print(login(username, password))
        elif command == "send_message":
            message = input("Message: ")
            receiver = input("Receiver: ")
            print(send_message(message, receiver))
        else:
            print("Unknown command")
```

---

## Setting a Cloud Storage Server _(Optional; only set up if your application requires file storage and access control)_

This optional setup enables a role-based cloud-like storage system alongside your server, providing secure file management with customizable permissions. Despite the playful name, it mirrors real-world cloud operations, offering an optimized, scalable filesystem with granular access control. Simply configure the storage server and define rules in the authorization model to get started.

Run this command to generate a fully-integrated RBAC-based filesystem with your `AsyncServer`.

```bash
python -m Fluxon.StartProject AsyncServer --cloud path/to/project
```

That's your new `server.py` with a `CloudStorageServer` integration:

```python
from Fluxon.Endpoint import AsyncServer, CloudStorageServer, run_server
import router

run_server(AsyncServer(
    port=8080, secure=False,
    setup=router.setup,

    # cloud storage setup, clean and elegant
    cloud_storage=CloudStorageServer(
        port=8888, secure=False,
    )
))
```

And the code for `router.py`:

```python
import pathlib
from Fluxon.Routing import Setup, dynamic_views_loading
from Fluxon.Database.APIs import SQLiteDatabase
from Fluxon.Security import Secrets
from authorization_model import CloudAuthorizationModel
import views, models

BASE_DIR = pathlib.Path("automatically_generated/path/to/project")

SECRETS_DIR = BASE_DIR / "secrets"
DATABASE_SCHEMA_DIR = BASE_DIR / "database_schema"
DATABASE_PATH = BASE_DIR / "database.sqlite3"
CLOUD_FOLDER = BASE_DIR / "cloud" # ← this one right here points to the directory of the entire filesystem

setup = Setup(
    # Routing models & views
    mapping=dynamic_views_loading(views), # ← maps all functions in the module `view` to their names implicitly (e.g., {..."login": views.login,...})
    models=models,

    # Server setup
    secrets=Secrets(SECRETS_DIR),
    database_schema_dir=DATABASE_SCHEMA_DIR,
    database_path=DATABASE_PATH,
    database_api=SQLiteDatabase,

    # Cloud storage setup
    cloud_folder=CLOUD_FOLDER,
    cloud_auth_model=CloudAuthorizationModel
)
```

---

Write your authorization models in `authorization_model.py`, you will find an automatically-generated one that looks like so:

```python
from Fluxon.Cloud.AuthorizationModels import RoleBasedAccessControl, Permissions, DefaultRole, AnonymousPermissions

# write as many authorization models as you want
# you can alternate between models in `router.py`

class CloudAuthorizationModel(RoleBasedAccessControl):
    # roles and permissions definition goes here...
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

    # set default role as viewer (remove the statement or replace it by `None` if to disable)
    DefaultRole(viewer)
    AnonymousPermissions(
        permissions=[
            # anonymous users get zero permissions (in this example at least)
        ]
    )
```

The `CloudAuthorizationModel` implements a **role-based access control (RBAC)** system. To define roles, subclass `RoleBasedAccessControl` and declare nested classes inheriting from `RoleBasedAccessControl.Role`. Each role specifies a `permissions` list using the `Permissions` enum (e.g., `Permissions.READ_FILE`). Available permissions include:

- `CREATE_FILE`
- `READ_FILE`
- `WRITE_FILE`
- `DELETE_FILE`
- `CREATE_SUB_DIRECTORY`
- `DELETE_SUB_DIRECTORY`
- `READ_TREE_DIRECTORY`
- `ASSIGN_ROLES` _(allows the role with this permission to assign roles to other users to file/folder)_

+ **Subdirectories and files inherit parent roles if children roles were not specified**
+ **Assigned roles for subdirectories and files overrides parents permissions, until this sub-role is removed**

Assign a default role with `DefaultRole(YourRoleClass)` to handle unauthenticated users with explicit roles. Configure anonymous access via `AnonymousPermissions(permissions=[...])`, which by default (in this example), has no permissions at all. Integrate this model in `router.py` by importing and simply passing it in the routing configuration `cloud_auth_model` (take a look at the previous `router.py` example for 
more context).

---

You can manage roles and permissions directly from `views.py`, here are two simple examples to views-cloud filesystem interactions and dynamics:
```python
from authorization_model import CloudAuthorizationModel
from models import User
from Fluxon.Database.Query import where

async def assign_user_as_viewer(request): #  a typical view in your `views.py`
    if request.user:
        # payload extraction
        user_to_assign = request.payload['user_to_assign']
        path = request.payload['path']
        # authorization
        if CloudAuthorizationModel.can_assign_roles( # ← checks for user's authority
            # if the user has `Permissions.ASSIGN_ROLES` on the path given, the function `can_assign_roles` returns `True`
            path=path, user=request.user
        ):
            # make sure the username exists
            if User.Check(where[User.username == user_to_assign]):
                # assign role to user
                status = CloudAuthorizationModel.assign_role( 
                    role=CloudAuthorizationModel.viewer,
                    username=user_to_assign,   # you can use `user` (`Fluxon.Routing.AuthenticatedUser` object, like `request.user`), `user_id`, or 'username' to identify users in cloud interactions, so you don't have to do a lot of queries
                    path=path
                )
                return status # ← this reports a brief summary of whatever happened in here to the client, example down below:
                """
                status = {
                    "user_assigned": "username: Jake; id: 12",
                    "cloud_relative_path": "/root/path/to/item",
                    "role": "viewer",
                    "status": "role assigned successfully"
                }
                """
            else:
                return {"response": f"user {user_to_assign} not found"}
        else:
            return {"response": f"you can't assign roles to users on this path ({cloud_relative_path})"}
    else:
        return {"response": "login needed"}

async def assign_me_as_owner(request):
    if request.user:
        cloud_relative_path = request.payload['path']
        # in this example, 'owner' role is granted to the creator of the file only
        if CloudAuthorizationModel.filesystem.path(cloud_relative_path).creator == request.user: # ← insures the user is creator of the file
            # `CloudAuthorizationModel.assign_role` is not dictated by a specific pattern, so you can apply your own logic to it
            status = CloudAuthorizationModel.assign_role(
                user=request.user,
                path=cloud_relative_path,
                role=CloudAuthorizationModel.owner
            )
            return status
        else:
            return {"response": "you're not the creator of this directory, ownership refused"}
    else:
        return {"response": "unauthenticated user, login needed"}
```
---

> The same models we worked with previously will be automatically integrated with the RBAC models like in this diagram right under. Pay close attention to how they're all intertwined with the `AuthenticatedUser` model, like we see in most user-centralized systems. _(integrated access control tables include `filesystem_permissions`, `filesystem_role_permissions`, `filesystem_roles`, `filesystem_constraints`, `filesystem_items`, `filesystem_audit_logs`, and `filesystem_assigned_roles`)_

---
<p align="center">
  <img src="https://raw.githubusercontent.com/Atiyakh/Fluxon/refs/heads/main/diagrams/cloud_integrated_models.png" alt="Example: Cloud Integrated Models Diagram.png">
</p>

---

### But how does it work? 

It's all about the `Models.AuthenticatedUser` class and various `Cloud.AuthorizationModels` module components. `Cloud.AuthorizationModels.RoleBasedAccessControl` centralizes access control for the filesystem (both user authorization and permissions) while sessions and users authentication are handled by `Models.AuthenticatedUser` by the main endpoint under the hood.

And here is how the client interacts with them:

```python
from Fluxon.Connect import ConnectionInterface, CloudStorageConnector

# starting the connection
server_connection = ConnectionInterface(host='localhost', port=8080)
cloud_connection = CloudStorageConnector(host='localhost', port=8888)

# logging in
server_connection.send_request("login", {
    'username': "Jane",
    'password': "Jane123@abc"
})

# creating a directory in the cloud root dir
cloud_response = cloud_connection.create_directory(relative_path="/janes_dir")

# claim ownership of the directory. (in this model, ownership is granted to the user who creates the directory if they call "assign_me_as_owner" on it)
response = server_connection.send_request("assign_me_as_owner", {'path': "/janes_dir"})

cloud_response = cloud_connection.create_file(relative_path="/janes_dir/some_file.txt") # no need to claim ownership, the user inherits it from the parent directory `/janes_dir`
cloud_response = cloud_connection.write_file(relative_path="/janes_dir/some_file.txt", data=b"some text... 123, some more text @#$abc") # no need to claim ownership, the user inherits it from the parent directory `/janes_dir`

# assign Mike as a viewer to `/janes_dir/some_file.txt`. Jane can since she's assigned as 'owner' to the file, and the role 'owner' has `ASSIGN_ROLES` in its permissions 
response = server_connection.send_request("assign_user_as_viewer", {'user_to_assign': "Mike", 'path': "/janes_dir"})
```

---

## Filesystem API — Low-Level Interface

The `Filesystem` module gives you a fine-grained, low-level interface to interact with files and directories directly from your server logic. This is useful for when you're writing advanced views, background tasks, or performing maintenance operations, or applying a complex logic that requires fine-grind filesystem operations, all while respecting RBAC constraints.

Each cloud item is an instance of `Filesystem.File` or `Filesystem.Directory`, both inheriting from `Filesystem.Item`.

---

### Operations on `Filesystem.Directory`

| Method                    | Description                                              |
| ------------------------- | -------------------------------------------------------- |
| `create_file(name)`       | Creates a new file in this directory.                    |
| `create_directory(name)`  | Creates a subdirectory.                                  |
| `list_items()`            | Lists files and folders within.                          |
| `delete()`                | Deletes the directory and its contents recursively.      |
| `parent()`                | Returns the parent directory.                            |
| `exists()`                | Returns whether the directory currently exists.          |
| `audit_logs()`            | Returns the access log for this directory.               |
| `move(new_path)`          | [*experimental*] Move this directory to a new location.  |

### Operations on `Filesystem.File`

| Method                    | Description                                                                                |
| ------------------------- | ------------------------------------------------------------------------------------------ |
| `read()`                  | Returns the file contents.                                                                 |
| `write(content)`          | Overwrites the file with given data.                                                       |
| `delete()`                | Deletes the file.                                                                          |
| `parent()`                | Returns the parent directory.                                                              |
| `exists()`                | Returns whether the file exists.                                                           |
| `audit_logs()`            | Returns chronological log of interactions. (returns a list of `Filesystem.Action` objects) |
| `last_modified()`         | Returns last modified timestamp.                                                           |
| `move(new_path)`          | [*experimental*] Move this file to a new location.                                         |

### `Filesystem.Action`

Audit logs track each interaction with any file or directory via the `Filesystem.Action` object:

| Attribute     | Type                | Description                                            |
| ------------- | ------------------- | ------------------------------------------------------ |
| `user`        | `AuthenticatedUser` | The user who triggered the action.                     |
| `item`        | `Filesystem.Item`   | The target of the action.                              |
| `action_type` | `str`               | `"read"`, `"write"`, `"delete"`, `"assign_role"`, etc. |
| `timestamp`   | `datetime.datetime` | When the action occurred.                              |

### Filesystem.Item (Base Class)

All files and directories have these attributes

| Attribute    | Type                | Description                                                |
| ------------ | ------------------- | ---------------------------------------------------------- |
| `name`       | `str`               | The item name (filename or directory name).                |
| `path`       | `pathlib.Path`      | Full path of the item within the virtual cloud filesystem. |
| `type`       | `str`               | Either `"file"` or `"directory"`.                          |
| `creator`    | `AuthenticatedUser` | Who originally created the item.                           |
| `size`       | `int`               | Item size in bytes (directories = 0).                      |
| `created_at` | `datetime.datetime` | Timestamp of creation.                                     |

> All of those functions will commit actions in the name of `Admin`, audits and logs will show `Admin` in the user slot unless an actual user were declared (e.g., `CloudAuthorizationModel.filesystem.path("/path/to/file/").write("Hello, World!", user=distinct_user) # assuming path will return a "filesystem.File" object`), in this case logs will show the user's name instead. files and folders marked as `Admin` CANNOT be accessed by other users unless `DefaultRole` says otherwise. Make sure to reference users if you incorporate low-level `Filesystem` operations in your main server logic to avoid `Admin` conflict unless intentional (why would you do that tho? 😕).

## Other future updates and features (TODOs)

- **Permission Granularity** Support more fine-grained permissions (e.g. read metadata vs content, time-limited access, shareable links, etc.). You can layer this in later.
- **Audit and Logging**	Expand the `filesystem_audit_logs` with automatic triggers for access events (reads, writes, role assignments).
- **Custom Constraints** Allow constraints at a role level (e.g., "collaborator can't delete root files") via filesystem_constraints could be powerful.
- **Conflict Resolution** What happens on concurrent file writes? Locking mechanisms or versioning may be needed depending on use. (that's actually important, how did I forgot about it 🤔)
- **Public File Access** Public-read access tokens or pre-signed URLs, or basically files with no constraints at all.
- **ABAC Support** Context-based access control might worth checking out. very difficult to pull off, but it's very worth it.

---

## Features

- **Independent Server Architecture:** Fluxon is not tied to browser-based interaction, making it ideal for real-time and unconventional server setups.
- **Simplified Reverse Requests:** Easily implement bidirectional communication without the complexity of WebSockets or low-level networking protocols.
- **Flexible Routing:** Intuitive mapping of request paths to view functions with support for asynchronous workflows, enabling seamless request handling.
- **Integrated Cloud Storage System:** Built-in cloud storage support acts like a media system (e.g., Django) but with unparalleled flexibility and server-side authorization.
- **Database Integration:** Use a Django-inspired ORM to define models and manage schemas with SQLite for streamlined database operations.
- **Secure Sessions:** Session-based authentication secured with private keys for robust communication.
- **Session Management:** Manage persistent client-server connections with advanced session handling.
- **Asynchronous Support:** Optimize performance with async-ready components for servers, databases, and views.

---

## What makes it different?

Fluxon offers a unique blend of flexibility, simplicity, and power for unconventional server architectures. Here's what makes Fluxon special:

### 1. Independent of Browsers

- Unlike frameworks like Django, Fluxon is not tied to browser-based interaction.
- This makes it ideal for applications requiring real-time or non-browser-based clients.

### 2. Simplified Reverse Requests

- Reverse requests are intuitive and easy to implement, eliminating the complexity of WebSockets or other low-level networking protocols.
- Developers with limited networking expertise can still implement robust, real-time, bidirectional communication.

### 3. Flexible Request Handling

- Fluxon allows highly customizable request handling with minimal effort.
- Define routes, map them to views, and integrate with asynchronous workflows to fit any server structure.

### 4. Integrated Cloud Storage System

- Fluxon features a built-in cloud storage system, offering:
  - Server-side flexibility with robust authorization mechanisms.
  - Client-side simplicity for seamless integration.
- No need for third-party storage systems, Fluxon’s solution is as easy to use as Django’s media system, but more customizable with built-in access control.

### 5. Perfect for Unconventional Server Architectures

- Fluxon thrives in environments where traditional frameworks fall short.
- Its modular design makes setting up servers, routers, models, views, and cloud storage straightforward and adaptable.
- Ideal for research-oriented, experimental, or highly customized applications.

---

## License

Fluxon is MIT licensed, free to use, modify, and break. If you’re as obsessed with networking as I am, let’s chat! (P.S. Try the cloud system, it’s weirdly fun.)
