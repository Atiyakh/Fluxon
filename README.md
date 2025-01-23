![](https://github.com/Atiyakh/Fluxon/blob/main/benchmarks/fluxon_logo.png)
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

- **Just Clone the repository to your local machine and you should be good to go**

```bash
git clone https://github.com/AtiyaKh/fluxon.git
```

---

## Getting Started

### Setting up The Server
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

```python
from Fluxon.Endpoint import AsyncServer, CloudStorageServer, run_server
import router

cloud_folder = "/path/to/cloud_folder"

server = run_server(AsyncServer(
    port=8080, secure=False,
    router=router.router,
    # cloud storage setup
    cloud_storage=CloudStorageServer(
        port=8888, secure=False,
        cloud_folder=cloud_folder
    )
))
```

---

### Router Setup
The `Router` handles all incoming requests and maps them to appropriate views.

and this is ```router.py``` that we used in ```server.py```
```python
from Fluxon.Routing import Router
import models, views

SERVER_SECURITY_KEY = "RsxZd5wVVml7C0H_LrbIVTDJU9kR-NwS1UxWD2lTVdY"
DATABASE_SCHEMA_DIR = "path/to/database_schema"
DATABASE_PATH = "path/to/database.sqlite3"

router = Router(
    # routing setup
    mapping={
        "signup": views.signup
    },
    # server setup
    private_key=SERVER_SECURITY_KEY,
    database_schema_dir=DATABASE_SCHEMA_DIR,
    database_path=DATABASE_PATH,
    models=models
)
```

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

+ **You should use a ```Models.AuthorizedUser``` model only once!**

#### 2. **Saving and Updating Database Schema**
Once the models are defined, you can save the schema, which Fluxon will translate into SQL queries. These queries will be stored as ```.sql``` files in your defined schema directory. This translation ensures that your models are reflected as actual SQL tables in your database.

saving schema is straightforward, type ```saveschema``` in the interactive server console, and the models you wrote will be automatically saved, loading that schema involved typing ```updateschema (schema number)``` in the server console. This should make alternating between schemas much easier.

#### 3. **Data Manipulations and Database Interactions**
Once the schema is set, Fluxon allows you to easily manipulate your data using ```Fluxon.Database.Manipulations.SqliteDatabase```, which is responsible for performing CRUD (Create, Read, Update, Delete) operations on your SQLite database.

```python
from Fluxon.Database.Manipulations import SqliteDatabase

db = SqliteDatabase("path/to/database_file")
```

Or you can use ```AsyncSqliteDatabase``` for full I/O support and non-blocking flow. Asynchronous database handling requires writing asynchronous views, which is not a bad idea at all. This version uses connection pooling to optimize database performance and avoid blocking. It also manages concurrent sql writing operations without locking the database file. (just use ```AsyncSqliteDatabase``` man)

```python
from Fluxon.Database.Manipulations import AsyncSqliteDatabase

async_db = AsyncSqliteDatabase("path/to/database_file")
```

- **Inserting Data:**

```python
db.User.Insert({
    db.User.username: "username",
    db.User.password: "password"
})
```

And here is an example for an ```AsyncSqliteDatabase``` implementation:

```python
await async_db.User.Insert({
    db.User.username: "username",
    db.User.password: "password"
})
```

The ```Insert``` query should automatically return the id of the inserted row, returns ```False``` if it fails.

- **Updating Data:**

```python 
db.User.Update({db.User.email: "newemail@example.com"}, db.where[db.User.username == "filtering by username"])
```

And this is how an async version look like, just remember to write async views

```python 
await async_db.User.Update({db.User.email: "newemail@example.com"}, db.where[db.User.username == "filtering by username"])
```

where statement accepts logical operators and ```&``` or ```|```

- **Querying Data:**
  
```python
users = db.User.Check(db.where[db.User.username == "name"], fetch=number_of_results)
```

```python
users = await async_db.User.Check(db.where[db.User.username == "name"], fetch=number_of_results)
```
  
you can also drop the fetch argument to get all the data filtered using where statement

- **Deleting Data:**
  
```python
db.User.Delete(where[db.User.id == 3])
```

```python
await db.User.Delete(where[db.User.id == 3])
```

Here is the thing tho, always add `await` before calling an asynchronous function, that way you're telling python to alternate between tasks and eliminate any I/O-related blocking 
(what am I sayin, you gon do it either way. the system crashes without awaiting coroutines bro)

---

### Views
Views are functions that handle specific requests. It can send any python object over the network, meaning that the client will receive the exact thing the view function returns, you can literally send an AI model with this if you want.

Example signup view from ```views.py```:

```python
def signup(request):
    User.Insert(request.pyload)
    return {"status": "200", "message": "Signed up successfully"}
```

And here is an asynchronous version of the same function (which is optimized for I/O systems, like the server we're working with right now)

```python
async def signup(request):
    """asynchronous view functions introduce way less blocking than synchronous ones"""
    await User.Insert(request.pyload)
    return {"status": "200", "message": "Signed up successfully"}
```

The request passed to the view is a ```Fluxon.Routing.Request``` object that contains the client's peername, session id, user id, the request payload, the connection object used by the server, and all the data you need. All requests passed are authenticated, you can authorize users (bind them to a user, which is supposed to be a Model.AuthorizedUser sub-class) using requests.login(user_id)

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
        sender = (await db.User.Check(db.where[db.User.id == request.userid], fetch=1, columns=['username']))[0][0]
        query = await db.User.Check(db.where[db.User.username == request.payload["to"]], fetch=1, columns=["id"])
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

Now this might sound a little complicated, just follow along to get yourself a cloud server

This is your new ```server.py```

```python
from Fluxon.Endpoint import AsyncServer, CloudStorageServer, run_server
import router

# this is the base directory for your cloud server
cloud_folder = "/path/to/cloud_folder"

server = run_server(AsyncServer(
    port=8080, secure=False,
    router=router.router,
    # cloud storage setup
    cloud_storage=CloudStorageServer(
        port=8888, secure=False,
        cloud_folder=cloud_folder
    )
))
```

This server setup integrates your ```CloudStorageServer``` in your main server ```AsyncServer```. (I will elaborate more on different server setups when I make other custom endpoints)

And here's the code for ```router.py```

```python
from Fluxon.Routing import Router
import cloud_models
import views

SERVER_SECURITY_KEY = "RsxZd5wVVml7C0H_LrbIVTDJU9kR-NwS1UxWD2lTVdY"
DATABASE_SCHEMA_DIR = "/path/to/database_schema"
DATABASE_PATH = "/path/to/database.sqlite3"

router = Router(
    # routing setup
    mapping={
        'signup': views.signup,
        'login': views.login,
        'create_owner': views.create_owner,
        'create_folder': views.create_folder,
        'write_file': views.write_file,
        'delete_item': views.delete_item,
        'read_file': views.read_file,
        'read_tree': views.read_tree
    },
    # server setup
    private_key=SERVER_SECURITY_KEY,
    database_schema_dir=DATABASE_SCHEMA_DIR,
    database_path=DATABASE_PATH,
    models=cloud_models # make sure to map the models to "cloud_models.py"
)
```

```cloud_models.py``` will collect the models for both servers and pass them to the router, and then the main server takes the models directly from the router to work with them. This way, the server can keep track of all your models and tables effectively.

Here is a possible ```cloud_models.py``` setup, you can go super fancy with it if you want. (I will write other sets of models for the cloud server and more operation flags for different operations in the future)

```python
from Fluxon.Database import Models
from models import User

class Owner(Models.Model):
    user = Models.OneToOneField(User, on_delete=Models.CASCADE)
    storage_limit = Models.BigIntegerField(default=10 * 1024 * 1024 * 1024)

class Directory(Models.Model):
    name = Models.CharField(max_length=255)
    directory = Models.ForeignKey('Directory', on_delete=Models.CASCADE)
    owner = Models.ForeignKey(Owner, on_delete=Models.CASCADE)
    created_at = Models.DateTimeField(auto_now_add=True)

class File(Models.Model):
    name = Models.CharField(max_length=255)
    directory = Models.ForeignKey(Directory, on_delete=Models.CASCADE)
    owner = Models.ForeignKey(Owner, on_delete=Models.CASCADE)
    size = Models.BigIntegerField()
    file_type = Models.CharField(max_length=50)
    created_at = Models.DateTimeField(auto_now_add=True)
    updated_at = Models.DateTimeField(auto_now=True)

class FileMetadata(Models.Model):
    file = Models.OneToOneField(File, on_delete=Models.CASCADE)
    is_encrypted = Models.BooleanField(default=False)
    encryption_algorithm = Models.CharField(max_length=100, null=True)
    last_accessed_at = Models.DateTimeField(auto_now=True)
```

And here is a good starting point for ```cloud_views.py```

```python
from Fluxon.Database.Manipulations import AsyncSQLiteDatabase
import pathlib, os

async_db = AsyncSQLiteDatabase("path/to/database.sqlite3")
cloud_folder = "path/to/cloud_folder"

async def signup(request):
    id = await async_db.User.Insert(request.payload)
    if id:
        return request.login(id)
    else:
        return False

async def login(request):
    query = (await async_db.User.Check(async_db.where[
        (async_db.User.username == request.payload['username']) & (async_db.User.password == request.payload['password'])
    ], fetch=1, columns=['id']))
    if query:
        id_ = query[0][0]
        return request.login(id_)
    else:
        return False

async def create_owner(request):
    if request.userid: # signed in
        rowid = await async_db.Owner.Insert({
            'user': request.userid,
            'storage_limit': 10 * 1024 * 1024 # 10 GB
        })
        # create a root directory for each user
        if rowid:
            username = (await async_db.User.Check(async_db.where[async_db.User.id == request.userid], fetch=1, columns=['username']))[0][0]
            request.grant_access(
                granted_operation=request.cloud_operations.create_directory, # as you can see operation flags are all encapsulated in the request itself for simplicity along side the basic `grant_access` authorization method. (enhanced access control features on the way!!)
                cloud_relative_path=username
            )
            return {
                "granted_operation": request.cloud_operations.create_directory,
                "cloud_path": username
            }
        else:
            return "Unable to create owner"
    else: return "login required"

async def create_folder(request): # create folder on cloud
    if request.userid: # signed in
        access_granted = True
        folder_path = pathlib.Path(request.payload['path'])
        query = (await async_db.Owner.Check(async_db.where[async_db.Owner.user == request.userid], fetch=1, columns=["id"]))
        if query:
            owner_id = query[0][0]
            # 1 check root owner
            root_parent = ((str(folder_path.parents[len(folder_path.parents) - 2])).replace('\\','')).replace('/','')
            query_2 = (await async_db.Directory.Check(async_db.where[(async_db.Directory.name == root_parent) & (async_db.Directory.directory == None)], fetch=1, columns=['owner']))
            if query_2:
                root_owner_id = query_2[0][0]
                if owner_id != root_owner_id:
                    access_granted = False
                    access_denied_message = f"AccessDenied: User does not have ownership of the root directory '{root_parent}'."
            else:
                return f"root folder not found {root_parent}"
            # 2 check folder parent exists
            if access_granted:
                if not pathlib.Path(os.path.join(cloud_folder, folder_path)).parent.exists():
                    access_granted = False
                    access_denied_message = f"AccessDenied: The parent directory '{folder_path.parent}' does not exist."
            # 3 check folder doesn't exist
            if access_granted:
                if pathlib.Path(os.path.join(cloud_folder, folder_path)).exists():
                    access_granted = False
                    access_denied_message = f"AccessDenied: The folder '{folder_path}' already exists."
            if access_granted:
                request.grant_access(
                    granted_operation=request.cloud_operations.create_directory,
                    cloud_relative_path=str(folder_path)
                )
                return {
                    "granted_operation": request.cloud_operations.create_directory,
                    "cloud_path": str(folder_path)
                }
            else: return access_denied_message
        return "authentication Failed; unregistered owner"
    else: return "login required"

async def write_file(request):
    if request.userid: # signed in
        access_granted = True
        file_path = pathlib.Path(request.payload['path'])
        query = (await async_db.Owner.Check(async_db.where[async_db.Owner.user == request.userid], fetch=1, columns=["id"]))
        if query:
            owner_id = query[0][0]
            # 1 check root owner
            root_parent = ((str(file_path.parents[len(file_path.parents) - 2])).replace('\\','')).replace('/','')
            query_2 = (await async_db.Directory.Check(async_db.where[(async_db.Directory.name == root_parent) & (async_db.Directory.directory == None)], fetch=1, columns=['owner']))
            if query_2:
                root_owner_id = query_2[0][0]
                if owner_id != root_owner_id:
                    access_granted = False
                    access_denied_message = f"AccessDenied: User does not have ownership of the root directory '{root_parent}'."
            else:
                return f"root folder not found {root_parent}"
            # 2 check folder parent exists
            if access_granted:
                if not pathlib.Path(os.path.join(cloud_folder, file_path)).parent.exists():
                    access_granted = False
                    access_denied_message = f"AccessDenied: The parent directory '{file_path.parent}' does not exist."

            if access_granted:
                request.grant_access(
                    granted_operation=request.cloud_operations.write_file,
                    cloud_relative_path=str(file_path)
                )
                return {
                    "granted_operation": request.cloud_operations.write_file,
                    "cloud_path": str(file_path)
                }
            else: return access_denied_message
        return "authentication Failed; unregistered owner"
    else: return "login required"

async def delete_item(request):
    if request.userid: # signed in
        access_granted = True
        file_path = pathlib.Path(request.payload['path'])
        query = (await async_db.Owner.Check(async_db.where[async_db.Owner.user == request.userid], fetch=1, columns=["id"]))
        if query:
            owner_id = query[0][0]
            # 1 check root owner
            root_parent = ((str(file_path.parents[len(file_path.parents) - 2])).replace('\\','')).replace('/','')
            query_2 = (await async_db.Directory.Check(async_db.where[(async_db.Directory.name == root_parent) & (async_db.Directory.directory == None)], fetch=1, columns=['owner']))
            if query_2:
                root_owner_id = query_2[0][0]
                if owner_id != root_owner_id:
                    access_granted = False
                    access_denied_message = f"AccessDenied: User does not have ownership of the root directory '{root_parent}'."
            else:
                return f"root folder not found {root_parent}"
            # 2 check item exists
            if access_granted:
                if not pathlib.Path(os.path.join(cloud_folder, file_path)).exists():
                    access_granted = False
                    access_denied_message = f"AccessDenied: Item '{file_path}' does not exist."

            if access_granted:
                request.grant_access(
                    granted_operation=request.cloud_operations.delete_item,
                    cloud_relative_path=str(file_path)
                )
                return {
                    "granted_operation": request.cloud_operations.delete_item,
                    "cloud_path": str(file_path)
                }
            else: return access_denied_message
        return "authentication Failed; unregistered owner"
    else: return "login required"

async def read_file(request):
    if request.userid: # signed in
        access_granted = True
        file_path = pathlib.Path(request.payload['path'])
        query = (await async_db.Owner.Check(async_db.where[async_db.Owner.user == request.userid], fetch=1, columns=["id"]))
        if query:
            owner_id = query[0][0]
            # 1 check root owner
            root_parent = ((str(file_path.parents[len(file_path.parents) - 2])).replace('\\','')).replace('/','')
            query_2 = (await async_db.Directory.Check(async_db.where[(async_db.Directory.name == root_parent) & (async_db.Directory.directory == None)], fetch=1, columns=['owner']))
            if query_2:
                root_owner_id = query_2[0][0]
                if owner_id != root_owner_id:
                    access_granted = False
                    access_denied_message = f"AccessDenied: User does not have ownership of the root directory '{root_parent}'."
            else:
                return f"root folder not found {root_parent}"
            # 2 check file exists
            if access_granted:
                if not pathlib.Path(os.path.join(cloud_folder, file_path)).is_file():
                    access_granted = False
                    access_denied_message = f"AccessDenied: file '{file_path}' does not exist."

            if access_granted:
                request.grant_access(
                    granted_operation=request.cloud_operations.read_file,
                    cloud_relative_path=str(file_path)
                )
                return {
                    "granted_operation": request.cloud_operations.read_file,
                    "cloud_path": str(file_path)
                }
            else: return access_denied_message
        return "authentication Failed; unregistered owner"
    else: return "login required"

async def read_tree(request):
    if request.userid: # signed in
        access_granted = True
        folder_path = pathlib.Path(request.payload['path'])
        query = (await async_db.Owner.Check(async_db.where[async_db.Owner.user == request.userid], fetch=1, columns=["id"]))
        if query:
            owner_id = query[0][0]
            # 1 check root owner
            root_parent = ((str(folder_path.parents[len(folder_path.parents) - 2])).replace('\\','')).replace('/','')
            query_2 = (await async_db.Directory.Check(async_db.where[(async_db.Directory.name == root_parent) & (async_db.Directory.directory == None)], fetch=1, columns=['owner']))
            if query_2:
                root_owner_id = query_2[0][0]
                if owner_id != root_owner_id:
                    access_granted = False
                    access_denied_message = f"AccessDenied: User does not have ownership of the root directory '{root_parent}'."
            else:
                return f"root folder not found {root_parent}"
            # 2 check folder parent exists
            if access_granted:
                if not pathlib.Path(os.path.join(cloud_folder, folder_path)).parent.exists():
                    access_granted = False
                    access_denied_message = f"AccessDenied: The parent directory '{folder_path.parent}' does not exist."
            # 3 check folder exist
            if access_granted:
                if not pathlib.Path(os.path.join(cloud_folder, folder_path)).is_dir():
                    access_granted = False
                    access_denied_message = f"AccessDenied: The folder '{folder_path}' does not exists."
            if access_granted:
                request.grant_access(
                    granted_operation=request.cloud_operations.read_tree,
                    cloud_relative_path=str(folder_path)
                )
                return {
                    "granted_operation": request.cloud_operations.read_tree,
                    "cloud_path": str(folder_path)
                }
            else: return access_denied_message
        return "authentication Failed; unregistered owner"
    else: return "login required"
```

The code sets the bases of how to authorize users to the cloud server. Use ```request.grant_access``` to authorize users to specific cloud operations, you can see the different flags for different operations like creating a folder, or writing a file, etc...

And here's how things look like on the client side

```python
from Fluxon.Connect import ConnectionHandler, CloudStorageConnector

conn = ConnectionHandler('192.168.1.6', 8080)
cloud = CloudStorageConnector('192.168.1.6', 8888)

# login request
response = conn.send_request("login", {
    "username": "Jack",
    "password": "Jack@123",
    "email": "Jack@gmail.com"
})

file_to_upload = "path/to/file"
cloud_relative_path = "username/path/to/file"

# each cloud-related request returns a specifically tailored cloud request for your operation
cloud_request = conn.send_request("write_file", {"path": cloud_relative_path})
# redirect the request, coupled with the main server session_id, to perform different cloud operations
with open(file_to_upload, 'rb') as file:
    cloud_response = cloud.send_request(cloud_request, conn.sessionid, payload=file.read())

# deleting a file
cloud_request = conn.send_request("delete_item", {"path": cloud_relative_path})
cloud_response = cloud.send_request(cloud_request, conn.sessionid)

# creating a directory
cloud_request = conn.send_request("create_folder", {"path": cloud_relative_path})
cloud_response = cloud.send_request(cloud_request, conn.sessionid)
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
- **Asynchronous Support:** Optimize performance with async-ready components for servers, databases, and views. Fluxon.AsyncServer is 21% faster than Django (see [benchmark testcases](https://github.com/Atiyakh/Fluxon/tree/main/benchmarks))

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
