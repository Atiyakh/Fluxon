# Fluxon

Fluxon is a lightweight Python backend framework that simplifies backend development. It offers routing, secure communication, session handling, and database management, making it an excellent choice for building server-side applications.

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
    git clone https://github.com/your-username/fluxon.git
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

Fluxon.Endpoint.AsyncServer is a versatile, robust, and flexiable session-based server infrastructure that supports asynchronous connections, which is the best option for most server setups

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
Once the schema is set, Fluxon allows you to easily manipulate your data using the Fluxon.Database.Manipulations.SqliteDatabase object, which is responsible for performing CRUD (Create, Read, Update, Delete) operations on your SQLite database.

```python
from Fluxon.Database.Manipulation import SqliteDatabase

db = SqliteDatabase("path/to/database_file")
```

- **Inserting Data:**

  ```python
  db.User.insert({
      db.User.username: "username",
      db.User.password: "password"
  })
  ```

  and the query should return the id of the inserted row

- **Updating Data:**

  ```python 
  db.update(User, {db.User.email: "newemail@example.com"}, db.where[db.User.username == "filtering by username"])
  ```

  where accepts logical operators and ```&``` or ```|```

- **Querying Data:**
  
  ```python
  users = db.User.Check(db.where[db.User.username == "name"], fetch=number_of_results)
  ```
  
  you can also drop the fetch argument to get all the data filtered by the where statement


- **Deleting Data:**
  
  ```python
  db.User.Delete(User, where[db.User.id == 3])
  ```

## Views
Views are functions that handle specific requests. It can send any python object over the network, meaning that the client will receive the exact thing the view function returns, you can literally send an AI model with this if you want.

Example signup view from "views.py":

```python
def signup(request):
    User.Insert(request.pyload)
    return {"status": "200", "message": "Signed up successfully"}
```

The request passed to the view is a Fluxon.Routing.Request object that contains the client's peername, session id, user id, the request payload, the connection object used by the server, and all the data you need. All the Requests passed are authenticated, you can authorize users (bind then to a user, which is supposed to be an Model.AuthorizedUser sub-class) user requests.login(user_id)

## Client Interaction
Fluxon provides a ConnectionHandler for managing client-server communication.

### Setting Up a Client

```python
from Fluxon.Connect import ConnectionHandler

conn = ConnectionHandler(host="127.0.0.1", port=8080)

# Example request
response = conn.send_request("signup", {"username": "test", "password": "test123"})
print(response)
Features
Routing
Map request paths to specific view functions for organized request handling.

Secure Communication
Uses session-based authentication secured by a private key.
```

## Running the Server
Start the server by running your routing configuration:

```bash
python server.py
```

The server will automatically run an interactive console so you can interact directly with the server using the console, like updating the database schema, or terminating, debugging, etc....

---

## Features

- **Routing:** Map request paths to specific view functions for organized request handling.
- **Database Integration:** Use SQLite and define schemas for easy database management.
- **Secure Sessions:** Session-based authentication secured with a private key.
- **Python Object Serialization:** Easily send and receive complex Python objects using `pickle`.
- **Session Management:** Manage persistent client-server communication.

---

## License
This project is licensed under the MIT License.
