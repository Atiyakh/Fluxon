# Fluxon

Fluxon is a lightweight python-based general-purpose network engine. It offers routing, secure communication, session handling, and database management, making it an excellent choice for building server-side applications.

---

## Table of Contents
1. [Installation](#installation)
2. [Getting Started](#getting-started)
3. [Features](#features)
5. [License](#license)

---

## Installation

- **Just Clone the repository to your local machine and you should be good to go:**

    ```bash
    git clone https://github.com/AtiyaKh/fluxon.git
    ```

---

## Getting Started

## Setting up The Server
Setting up the server is pretty simple. First you pick your favorite server from Fluxon.Endpoint, let's say you happened to choose AsyncServer as your main Endpoint for the server (which is the only one avaliable right now, more on the way tho)

write this in your "server.py"
```python
from Fluxon.Endpoint import AsyncServer, run_server
import router

server = run_server(AsyncServer(
    port=8080, secure=False,
    router=router.router
))
```

Fluxon.Endpoint.AsyncServer is a versatile, robust, and flexiable session-based server infrastructure that supports asynchronous connections and reverse requests, which is the best option for most server setups

You can also equip the server with a built-in highly-optimized cloud storage server, but it requires a complex setup and authorization mechanism. We'll talk about it in a second.

```python
from Fluxon.Endpoint import AsyncServer, CloudStorageServer, run_server
import router

cloud_folder = r"C:\Users\skhodari\Desktop\TESTING\cloud_folder"

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

### Router Setup
The `Router` handles all incoming requests and maps them to appropriate views.

and this is "router.py" that we used in "server.py"
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

## Database Management
### Database Integration in Fluxon

Fluxon provides a seamless way to integrate a database with your application using an SQLite backend. The process is similar to Django’s ORM but with additional flexibility, allowing you to define models, manage schemas, and manipulate data easily. Here's a breakdown of the database workflow:

### 1. **Defining Models**
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

### 2. **Saving and Updating Database Schema**
Once the models are defined, you can save the schema, which Fluxon will translate into SQL queries. These queries will be stored as ```.sql``` files in your defined schema directory. This translation ensures that your models are reflected as actual SQL tables in your database.

saving schema is straightforward, type ```saveschema``` in the interactive server console, and the modles you wrote will be automatically saved, loading that schema involved typeing ```updateschema (schema number)``` in the server console. This should make alternating between schemas much easier.

### 3. **Data Manipulation**
Once the schema is set, Fluxon allows you to easily manipulate your data using the ```Fluxon.Database.Manipulations.SqliteDatabase``` object, which is responsible for performing CRUD (Create, Read, Update, Delete) operations on your SQLite database.

```python
from Fluxon.Database.Manipulation import SqliteDatabase

db = SqliteDatabase("path/to/database_file")
```

Or you can use ```AsyncSqliteDatabase``` for full I/O support and non-blocking flow. Asynchronous database handling requires writing asynchronous, which is not a bad idea by any means. This version uses connections pool to optimize database performace and avoid blocking. It also manages csoncurrent sql writings (setting ```check_same_thread``` to ```False```) without blocking the file.  

```python
from Fluxon.Database.Manipulation import AsyncSqliteDatabase

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
  db.update(User, {db.User.email: "newemail@example.com"}, db.where[db.User.username == "filtering by username"])
  ```

  And this is how an async version look like, just remember to write async views

  ```python 
  await async_db.update(User, {db.User.email: "newemail@example.com"}, db.where[db.User.username == "filtering by username"])
  ```

  where accepts logical operators and ```&``` or ```|```

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

## Views
Views are functions that handle specific requests. It can send any python object over the network, meaning that the client will receive the exact thing the view function returns, you can literally send an AI model with this if you want.

Example signup view from "views.py":

```python
def signup(request):
    User.Insert(request.pyload)
    return {"status": "200", "message": "Signed up successfully"}
```

And here is an asynchronous version of the same function (which is optimized for I/O systems, like the server we're working with right now)

```python
async def signup(request):
    """this view function introduces less blocking than the synchronous version"""
    await User.Insert(request.pyload)
    return {"status": "200", "message": "Signed up successfully"}
```

The request passed to the view is a Fluxon.Routing.Request object that contains the client's peername, session id, user id, the request payload, the connection object used by the server, and all the data you need. All the Requests passed are authenticated, you can authorize users (bind then to a user, which is supposed to be a Model.AuthorizedUser sub-class) using requests.login(user_id)

## Client Interaction
Fluxon provides high-level class ```ConnectionHandler``` for managing client-side communication.

### Setting Up a Client

You can use this on the client side of your application, it manages sessions and socket connections automatically, and organizes the request send and receive process. It also keeps an open socket holding the same session id for reverse requests (from the server to the client) it allows for multiple requests for the same session at the same time, which is dope for a higher-level connection interface.

```python
from Fluxon.Connect import ConnectionHandler

conn = ConnectionHandler(host="127.0.0.1", port=8080)

# Example request
response = conn.send_request("signup", {"username": "test", "password": "test123"})
print(response)
```

## Running the Server
Start the server by running your routing configuration:

```bash
python server.py
```

The server will automatically run an interactive console so you can interact directly with the server using the console, like updating the database schema, or terminating, debugging, etc....

## Setting a Cloud Storage Server (optional; for complex server structures)

Now this might sound a little complicated, just follow along to get yourself a cloud server

This is your new ```server.py```

```python
from Fluxon.Endpoint import AsyncServer, CloudStorageServer, run_server
import router

# this is the base directory for your cloud server
cloud_folder = r"C:\Users\skhodari\Desktop\TESTING\cloud_folder"

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

This is the server setup, you will typically integrate your ```CloudStorageServer``` in the main server ```AsyncServer```.

And ```router.py```

```python
from Fluxon.Routing import Router
import cloud_models
import views

SERVER_SECURITY_KEY = "RsxZd5wVVml7C0H_LrbIVTDJU9kR-NwS1UxWD2lTVdY"
DATABASE_SCHEMA_DIR = r"C:\Users\skhodari\Desktop\TESTING\database_schema"
DATABASE_PATH = r"C:\Users\skhodari\Desktop\TESTING\database.sqlite3"

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

```cloud_models.py``` will collect the models for both servers and pass them to the router, and then the main server takes the models directly from the router.

Here is a possible ```cloud_models.py``` setup, you can go super fancy with it if you want.

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

And here is a good start for ```views.py```

```python
from Fluxon.Database.Manipulations import AsyncSQLiteDatabase
import pathlib, os

async_db = AsyncSQLiteDatabase(r"C:\Users\skhodari\Desktop\TESTING\database.sqlite3")
cloud_folder = r"C:\Users\skhodari\Desktop\TESTING\cloud_folder"

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
                granted_operation=request.cloud_operations.create_directory,
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
    if request.userid: # singed in
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
    if request.userid: # singed in
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
    if request.userid: # singed in
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
    if request.userid: # singed in
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
    if request.userid: # singed in
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

The code sets the bases of how to authorize users to the cloud server. Use ```request.grant_access``` to authorize users to specific cloud operations, you can see the different flags for different operations like creating a folder, oe writing a file, etc...

And here's how things look like on the client side

```python
from Fluxon.Connect import ConnectionHandler, CloudStorageConnector

conn = ConnectionHandler('192.168.1.6', 8080)
cloud = CloudStorageConnector('192.168.1.6', 8888)

# login request
response = conn.send_request("login", {
    "username": "AtiyaKh",
    "password": "Atty@kh123",
    "email": "atiyaalkhodari1@gmail.com"
})

file_to_upload = "path/to/file"
cloud_relative_path = "username/path/to/file"

# write_file returns a specifically tailored cloud request for your operation  
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

- **Routing:** Map request paths to specific view functions for organized request handling.
- **Database Integration:** Use SQLite and define schemas for easy database management.
- **Secure Sessions:** Session-based authentication secured with a private key.
- **Python Object Serialization:** Easily send and receive complex Python objects using `pickle`.
- **Session Management:** Manage persistent client-server communication.
- **Cloud Storage Server:** built-in support for cloud storage.

---

## License
This project is licensed under the MIT License.
