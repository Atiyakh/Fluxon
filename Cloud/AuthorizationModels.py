import asyncio
import logging
import traceback
from Endpoint.auth_context import AuthenticatedUser
from Fluxon.Database.db_core_interface import DatabaseAPI, TableSQLite, AsyncTableSQLite
from enum import Flag, auto
import sqlite3
from logging import Logger
import datetime
import pathlib
import aiosqlite
import inspect

# Custom exception for when the authorized user model is not found
class AuthenticatedUserModelNotFound(Exception):
    """Raised when the authorized user model is not found in the database schema"""
    pass

# Utility function to check if a function is a coroutine and await it if necessary
async def await_if_coroutine(func, *args, **kwargs):
    if inspect.iscoroutinefunction(func):
        return await func(*args, **kwargs)
    return func(*args, **kwargs)


# SQL syntax varies slightly across different DBMSs so we will need to lookup the appropriate script
RBAC_SQL_TABLES = {
    "SQLite": lambda authorized_user_model: f"""
-- Roles Table
CREATE TABLE IF NOT EXISTS filesystem_roles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    role_name VARCHAR(150) UNIQUE NOT NULL
);

-- Permissions Table
CREATE TABLE IF NOT EXISTS filesystem_permissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    permission_name VARCHAR(150) UNIQUE NOT NULL
);

-- Role-Permission Relationship Table
CREATE TABLE IF NOT EXISTS filesystem_role_permissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    role_id INTEGER NOT NULL,
    permission_id INTEGER NOT NULL,
    FOREIGN KEY (role_id) REFERENCES filesystem_roles(id) ON DELETE CASCADE,
    FOREIGN KEY (permission_id) REFERENCES filesystem_permissions(id) ON DELETE CASCADE
);

-- (NOT IMPLEMENTED YET) Constraints Table [ABAC-like controls] (e.g., time-based access)
CREATE TABLE IF NOT EXISTS filesystem_constraints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    expiration_date DATE,
    valid_from TIME,
    valid_until TIME
    -- Additional constraint fields can be added
);

-- Assigned Roles Table
CREATE TABLE IF NOT EXISTS filesystem_assigned_roles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    assigned_item_id INTEGER,
    role_id INTEGER NOT NULL,
    constraints_id INTEGER,
    FOREIGN KEY (user_id) REFERENCES {authorized_user_model}(id) ON DELETE CASCADE,
    FOREIGN KEY (assigned_item_id) REFERENCES filesystem_items(id) ON DELETE CASCADE,
    FOREIGN KEY (role_id) REFERENCES filesystem_roles(id) ON DELETE CASCADE,
    FOREIGN KEY (constraints_id) REFERENCES filesystem_constraints(id) ON DELETE CASCADE
);

-- Filesystem/Resources Table
CREATE TABLE IF NOT EXISTS filesystem_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_name VARCHAR(150) NOT NULL,
    item_path VARCHAR(150) NOT NULL,
    item_type VARCHAR(150) NOT NULL CHECK (item_type IN ('file', 'directory')), -- 'file' or 'directory'
    size INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    modified_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    owner_user_id INTEGER,
    parent_item_id INTEGER CHECK (parent_item_id IS NULL OR id != parent_item_id), -- no self-referencing / allow root dir (cycle references solved elsewhere)
    FOREIGN KEY (owner_user_id) REFERENCES {authorized_user_model}(id) ON DELETE CASCADE,
    FOREIGN KEY (parent_item_id) REFERENCES filesystem_items(id) ON DELETE CASCADE
);

-- Audit Logs Table
CREATE TABLE IF NOT EXISTS filesystem_audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    item_id INTEGER NOT NULL,
    action VARCHAR(150) NOT NULL,  -- left loose on purpose!
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES {authorized_user_model}(id) ON DELETE CASCADE,
    FOREIGN KEY (item_id) REFERENCES filesystem_items(id) ON DELETE CASCADE
);
""",

    "MySQL": lambda authorized_user_model: f"""
-- Roles Table
CREATE TABLE IF NOT EXISTS filesystem_roles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    role_name VARCHAR(150) UNIQUE NOT NULL
);

-- Permissions Table
CREATE TABLE IF NOT EXISTS filesystem_permissions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    permission_name VARCHAR(150) UNIQUE NOT NULL
);

-- Role-Permission Relationship Table
CREATE TABLE IF NOT EXISTS filesystem_role_permissions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    role_id INT NOT NULL,
    permission_id INT NOT NULL,
    FOREIGN KEY (role_id) REFERENCES filesystem_roles(id) ON DELETE CASCADE,
    FOREIGN KEY (permission_id) REFERENCES filesystem_permissions(id) ON DELETE CASCADE
);

-- Constraints Table (for ABAC-like controls)
CREATE TABLE IF NOT EXISTS filesystem_constraints (
    id INT AUTO_INCREMENT PRIMARY KEY,
    expiration_date DATE,
    valid_from TIME,
    valid_until TIME
    -- Additional constraint fields can be added
);

-- Assigned Roles Table
CREATE TABLE IF NOT EXISTS filesystem_assigned_roles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    assigned_item_id INT,
    role_id INT NOT NULL,
    constraints_id INT,
    FOREIGN KEY (user_id) REFERENCES {authorized_user_model}(id) ON DELETE CASCADE,
    FOREIGN KEY (assigned_item_id) REFERENCES filesystem_items(id) ON DELETE CASCADE,
    FOREIGN KEY (role_id) REFERENCES filesystem_roles(id) ON DELETE CASCADE,
    FOREIGN KEY (constraints_id) REFERENCES filesystem_constraints(id) ON DELETE CASCADE
);

-- Filesystem/Resources Table
CREATE TABLE IF NOT EXISTS filesystem_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    item_name VARCHAR(150) NOT NULL,
    item_path VARCHAR(150) NOT NULL,
    item_type VARCHAR(150) NOT NULL CHECK (item_type IN ('file', 'directory')),
    size INT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    modified_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    owner_user_id INT,
    parent_item_id INT,
    CHECK (parent_item_id IS NULL OR id != parent_item_id),
    FOREIGN KEY (owner_user_id) REFERENCES {authorized_user_model}(id) ON DELETE CASCADE,
    FOREIGN KEY (parent_item_id) REFERENCES filesystem_items(id) ON DELETE CASCADE
);

-- Audit Logs Table
CREATE TABLE IF NOT EXISTS filesystem_audit_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    item_id INT NOT NULL,
    action VARCHAR(150) NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES {authorized_user_model}(id) ON DELETE CASCADE,
    FOREIGN KEY (item_id) REFERENCES filesystem_items(id) ON DELETE CASCADE
);
""",
}

# all of the classes in this file are abstract classes, and will NOT be called during runtime, so we can use a simple dictionary to store model information

MODEL_INFO = dict() # ← this will be filled externally during startup for context

class Permissions(Flag):
    CREATE_FILE = auto()
    READ_FILE = auto()
    EDIT_FILE = auto()
    DELETE_FILE = auto()
    CREATE_SUB_DIRECTORY = auto()
    DELETE_SUB_DIRECTORY = auto()
    READ_TREE_DIRECTORY = auto()
    WRITE_FILE = auto()
    ASSIGN_ROLES = auto()

class Filesystem:
    class Item:
        name: str
        path: pathlib.Path
        type: str
        creator: AuthenticatedUser
        size: int
        created_at: str

    class Action:
        user: AuthenticatedUser
        item: 'Filesystem.Item'
        action_type: str
        timestamp: str

    class Directory(Item):
        def create_file(self, name:str) -> bool:
            """Create a file in the directory"""
            pass

        def create_directory(self, name:str) -> bool:
            """Create a sub-directory in the directory"""
            pass

        def list_items(self) -> 'list[Filesystem.File | Filesystem.Directory]':
            """List all items (files and directories) in the directory"""
            pass

        def delete(self) -> bool:
            """Delete the directory and its contents"""
            pass

        def parent(self) -> 'list[Filesystem.Directory]':
            """Get the parent directory of the current directory"""
            pass

        def exists(self) -> bool:
            """Check if the directory exists"""
            pass

        def audit_logs(self) -> 'list[Filesystem.Action]':
            """Get the audit logs for the directory"""
            pass

        def move(self, new_path: pathlib.Path) -> bool:
            """[experimental] Move the directory to a new path"""
            pass
    
    class File(Item):
        def read(self) -> bytes:
            """Read the file content"""
            pass

        def write(self, content: bytes | str) -> bool:
            """Write content to the file"""
            pass

        def delete(self) -> bool:
            """Delete the file"""
            pass
        
        def parent(self) -> 'Filesystem.Directory':
            """Get the parent directory of the file"""
            pass

        def exists(self) -> bool:
            """Check if the file exists"""
            pass

        def audit_logs(self) -> 'list[Filesystem.Action]':
            """Get the audit logs for the file in a chronological order"""
            pass

        def last_modified(self) -> datetime:
            """Get the last modified timestamp of the file"""
            pass

        def move(self, new_path: pathlib.Path) -> bool:
            """[experimental] Move the file to a new path"""
            pass

class RoleBasedAccessControl:
    # NOTE `MODEL_INFO` is a global variable that will be filled in `Routing.Setup` during runtime
    #      and it will be accessed through this attribute `RoleBasedAccessControl.MODEL_INFO`
    MODEL_INFO = MODEL_INFO
    class Role: # abstract class
        """Base class for roles in the Role-Based Access Control system"""
        pass

    @staticmethod
    async def _check_AuthenticatedUser_model_exists(database:DatabaseAPI, authorized_user_model:str, logger:Logger) -> bool:
        """Check if the authorized user model exists in the database schema (Called as part of the startup tasks of CloudStorageServer)"""
        if hasattr(database, authorized_user_model):
            # check if the model exists in the database schema
            # `Database.db_core_interface.Table\AsyncTable._check_schema_exists` is a method that checks if the table exists in the database schema
            table_obj: TableSQLite | AsyncTableSQLite = getattr(database, authorized_user_model)
            check_schema_exists = table_obj._check_schema_exists
            try:
                exists = await_if_coroutine(check_schema_exists)
                if isinstance(exists, bool):
                    return exists
                else:
                    logger.error(f"[CloudStorageServer] Unexpected return value from '_check_schema_exists' for model '{authorized_user_model}': {exists!r}")
            except Exception as e:
                logger.error(f"[CloudStorageServer] Error checking schema existence for '{authorized_user_model}': {e}")
            return False

    @staticmethod
    async def _async_define_cloud_tables(database:DatabaseAPI, script:str, logger:Logger): # FIXME this method might need to be refactored after MySQL support is added
        conn:aiosqlite.Connection = await database.pool.get_connection()
        try:
            async with conn.cursor() as cursor:
                try:
                    await cursor.executescript(script)
                    await conn.commit()
                except sqlite3.DatabaseError as e:  # override `sqlite3.DatabaseError` to insert logs
                    logger.error(f"[CloudStorageServer-RBAC] Failed to define cloud filesystem tables - error: {e} - traceback: {traceback.format_exc()}")
                    raise sqlite3.Error(
                        "[CloudStorageServer-RBAC] Failed to define cloud filesystem tables"
                    )
                except Exception as e:
                    logger.error(f"[CloudStorageServer-RBAC] UnexpectedError: Failed to define cloud filesystem tables - error: {e} - traceback: {traceback.format_exc()}")
                    raise RuntimeError(
                        "[CloudStorageServer-RBAC] UnexpectedError: Failed to define cloud filesystem tables"
                    )  # NOTE finally statement removed, use context manager instead 
        finally:
            await database.pool.release_connection(conn)

    @staticmethod
    async def _define_cloud_tables(database:DatabaseAPI, logger:Logger, authorized_user_model):
        """Defines RBAC tables (Called as part of the startup tasks of CloudStorageServer)"""
        script = RBAC_SQL_TABLES[database.DBMS](authorized_user_model)
        if database.is_async:
            return await RoleBasedAccessControl._async_define_cloud_tables(
                database, script, logger
            )
        try:
            cursor = database.conn.cursor()
            cursor.executescript(script)
            database.conn.commit()
            cursor.close()
        except sqlite3.Error as e:
            logger.error(f"[CloudStorageServer-RBAC] Failed to define cloud filesystem tables - error: {e} - traceback: {traceback.format_exc()}")
            raise sqlite3.Error(
                "[CloudStorageServer-RBAC] Failed to define cloud filesystem tables"
            )
        except Exception as e:
            logger.error(f"[CloudStorageServer-RBAC] UnexpectedError: Failed to define cloud filesystem tables - error: {e} - traceback: {traceback.format_exc()}")
            raise RuntimeError(
                "[CloudStorageServer-RBAC] UnexpectedError: Failed to define cloud filesystem tables"
            )

    @staticmethod
    async def _async_insert_permissions(database:DatabaseAPI):
        available_permissions = [(getattr(Permissions, permission).name) for permission in dir(Permissions) if isinstance(getattr(Permissions, permission), Flag)]
        # inserting permissions
        permission_id_lookup = dict()
        permissions_async_table_obj:AsyncTableSQLite = getattr(database, "filesystem_permissions")
        for permission_name in available_permissions:
            if query := (await permissions_async_table_obj.Check(where=f'permission_name == "{permission_name}"', fetch=1, columns=['id'])):
                permission_id = query[0][0]
            else:
                permission_id = await permissions_async_table_obj.Insert(permission_name=permission_name)
            permission_id_lookup[permission_name] = permission_id
        return permission_id_lookup

    @staticmethod
    async def _insert_permissions(database:DatabaseAPI, logger:Logger):
        try:
            if database.is_async:
                return await RoleBasedAccessControl._async_insert_permissions(database)
            else:
                available_permissions = [(getattr(Permissions, permission).name) for permission in dir(Permissions) if isinstance(getattr(Permissions, permission), Flag)]
                # inserting permissions
                permission_id_lookup = dict()
                permissions_async_table_obj:TableSQLite = getattr(database, "filesystem_permissions")
                for permission_name in available_permissions:
                    if query := permissions_async_table_obj.Check(where=f'permission_name == "{permission_name}"', fetch=1, columns=['id']):
                        permission_id = query[0][0]
                    else:
                        permission_id = permissions_async_table_obj.Insert(permission_name=permission_name)
                    permission_id_lookup[permission_name] = permission_id
                return permission_id_lookup
        except Exception as e:
            logger.error(f"[CloudStorageServer-RBAC] UnexpectedError: Failed to define cloud filesystem tables - error: {e} - traceback: {traceback.format_exc()}")
            raise RuntimeError(
                "[CloudStorageServer-RBAC] UnexpectedError: Failed to define cloud permissions"
            )

    @staticmethod
    async def _async_insert_role_permissions(
        role_permissions_async_table_obj:AsyncTableSQLite,
        permission_id_lookup:dict,
        role_id:int, permissions:list):
        tasks = [
            role_permissions_async_table_obj.Insert(
                permission_id=permission_id_lookup[permission],
                role_id=role_id
            )
            for permission in permissions
        ]
        await asyncio.gather(*tasks)

    @staticmethod
    async def _async_insert_roles(roles_async_table_obj:AsyncTableSQLite, role_permissions_async_table_obj:AsyncTableSQLite, cloud_auth_model, permission_id_lookup:dict):
        await role_permissions_async_table_obj.Delete() # deleting previous permissions assigned to roles
        for role_name, permissions_list in MODEL_INFO["roles_permissions_lookup"].items():
            permissions = [permission.name for permission in permissions_list]
            # make sure that role exists (and retrieve role_id)
            if query := (await roles_async_table_obj.Check(where=f'role_name = "{role_name}"', fetch=1, columns=['id'])):
                role_id = query[0][0]
            else: # role is not registered yet
                role_id = (await roles_async_table_obj.Insert(role_name=role_name))
            # assign permissions to roles
            await RoleBasedAccessControl._async_insert_role_permissions(
                role_permissions_async_table_obj,
                permission_id_lookup, role_id,
                permissions
            )

    @staticmethod
    async def _insert_roles(database:DatabaseAPI, logger:Logger, cloud_auth_model, permission_id_lookup:dict):
        try:
            # extracting table objects from the database API
            roles_table_obj: TableSQLite | AsyncTableSQLite = getattr(database, "filesystem_roles")
            role_permissions_table_obj: TableSQLite | AsyncTableSQLite = getattr(database, "filesystem_role_permissions")
            if isinstance(roles_table_obj, AsyncTableSQLite):
                return await RoleBasedAccessControl._async_insert_roles(
                    # async tables' logic is different from sync tables, so we need to handle them separately
                    roles_async_table_obj=roles_table_obj,
                    role_permissions_async_table_obj=role_permissions_table_obj,
                    cloud_auth_model=cloud_auth_model,
                    permission_id_lookup=permission_id_lookup
                )
            else:
                role_permissions_table_obj.Delete() # deleting previous permissions assigned to roles
                for role_name, permissions_list in MODEL_INFO["roles_permissions_lookup"].items():
                    permissions = [permission.name for permission in permissions_list]
                    # make sure that role exists (and retrieve role_id)
                    if query := (roles_table_obj.Check(where=f'role_name = "{role_name}"', fetch=1, columns=['id'])):
                        role_id = query[0][0]
                    else: # role is not registered yet
                        role_id = roles_table_obj.Insert(role_name=role_name)
                    # assign permissions to roles
                    for permission in permissions:
                        role_permissions_table_obj.Insert(
                            permission_id=permission_id_lookup[permission],
                            role_id=role_id
                        )

        except Exception as e:
            logger.error(f"[CloudStorageServer-RBAC] UnexpectedError: Failed to define roles - error: {e} - traceback: {traceback.format_exc()}")
            raise RuntimeError(
                "[CloudStorageServer-RBAC] UnexpectedError: Failed to define roles"
            )

    @staticmethod
    async def _cloud_startup(cloud_auth_model, logger:logging.Logger, authorized_user_model) -> None:
        # initialize database API (NOTE: can be async or sync)
        database:DatabaseAPI = MODEL_INFO['database_api'](MODEL_INFO['database_path'])
        try:
            # check authorized user model exists
            if await RoleBasedAccessControl._check_AuthenticatedUser_model_exists(database, authorized_user_model, logger):
                # cloud authorization model startup
                await RoleBasedAccessControl._define_cloud_tables(database, logger, authorized_user_model)
                # call `refresh` for database structural changes
                database = await await_if_coroutine(database.refresh)
                # insert permissions and roles if don't exist and map them to roles
                permission_id_lookup = await RoleBasedAccessControl._insert_permissions(database, logger)
                await RoleBasedAccessControl._insert_roles(
                    database, logger, cloud_auth_model,
                    permission_id_lookup
                )
            else:
                logger.warn("[CloudStorageServer-RBAC] AuthenticatedUser model not found")
                raise AuthenticatedUserModelNotFound("[CloudStorageServer-RBAC] AuthenticatedUser model not found. Try to `updateschema` from the console to migrate your models if you already have one")
        except RuntimeError as e:
            logger.error(f"[CloudStorageServer-RBAC] Unexpected error while starting up cloud server | error: {e} traceback: {traceback.format_exc()}")
            raise RuntimeError(
                "[CloudStorageServer-RBAC] Unexpected error while starting up cloud server"
            )
    
    @staticmethod
    def _validate_operation(user_id, operation):
        print(user_id, operation, MODEL_INFO['db'])
    
    @staticmethod
    async def _get_user_id(user=None, user_id:int=None, username:str=None):
        if user is not None:
            if isinstance(user, int):
                user_id = user
            elif hasattr(user, 'id'):
                user_id = user.id
            elif hasattr(user, 'username'):
                username = user.username
        if user_id is None and username is not None:
            query = await MODEL_INFO['db'].user.Check(
                MODEL_INFO['db'].where[
                    MODEL_INFO['db'].user.username == username
                ], fetch=1, columns=["id"]
            )
            if query:
                user_id = query[0][0]
        return user_id

    @staticmethod 
    async def assign_role(path, role:Role, user=None, user_id:int=None, username:str=None):
        try:
            user_id = await RoleBasedAccessControl._get_user_id(user, user_id, username)
            query = await MODEL_INFO['db'].role.Check(MODEL_INFO['db'].where[
                MODEL_INFO['db'].role.role_name == role.__name__
            ], fetch=1, columns=["id"])
            if query:
                if await MODEL_INFO['db'].user_role.Insert({
                    "user_id": user_id, "role_id": query[0][0]
                }):
                    return True
                else:
                    return False
            else:
                return False
        except Exception as e:
            print(traceback.print_exc())
            print("[Fluxon-Cloud] Unable to assign user role |", e)
    
    @staticmethod
    async def get_user_permissions(path, user=None, user_id:int=None, username:str=None):
        try:
            user_id = await RoleBasedAccessControl._get_user_id(user, user_id, username)
            if not user_id:
                return []
            else:
                query = await MODEL_INFO['db'].user_role.Check(
                    MODEL_INFO['db'].where[
                        MODEL_INFO['db'].user_role.user_id == user_id
                    ], fetch=1, columns=["role_id"]
                )
                if query:
                    role_id = query[0][0]
                    permissions_query = await MODEL_INFO['db'].role_permission.Check(
                        MODEL_INFO['db'].where[
                            MODEL_INFO['db'].role_permission.role_id == role_id
                        ], fetch=1, columns=["permission_name"]
                    )
                    return [getattr(Permissions, permission[0]) for permission in permissions_query]
                else:
                    return []
        except Exception as e:
            print(traceback.print_exc())
            print("[Fluxon-Cloud] Unable to assign user role |", e)
    
    @staticmethod
    async def get_user_role(path, user=None, user_id:int=None, username:str=None):
        try:
            user_id = await RoleBasedAccessControl._get_user_id(user, user_id, username)
            if not user_id:
                return None
            else:
                query = await MODEL_INFO['db'].user_role.Check(
                    MODEL_INFO['db'].where[
                        MODEL_INFO['db'].user_role.user_id == user_id
                    ], fetch=1, columns=["role_id"]
                )
                if query:
                    role_id = query[0][0]
                    role_query = await MODEL_INFO['db'].role.Check(
                        MODEL_INFO['db'].where[
                            MODEL_INFO['db'].role.id == role_id
                        ], fetch=1, columns=["role_name"]
                    )
                    if role_query:
                        return getattr(RoleBasedAccessControl, role_query[0][0])
                    else:
                        return None
                else:
                    return None
        except Exception as e:
            print(traceback.print_exc())
            print("[Fluxon-Cloud] Unable to get user role |", e)

class DefaultRole:
    def __init__(self, default_role:RoleBasedAccessControl.Role):
        self.default_role = default_role

class AnonymousPermissions:
    def __init__(self, permissions:list):
        self.permissions = permissions
