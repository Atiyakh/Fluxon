from datetime import date, time, datetime
import sqlite3, aiosqlite
from asyncio import Queue
import mysql.connector
import logging
import types
import pathlib
import traceback

CREDENTIALS = dict()

# Query builder [includes Where, Clause, Column, Table/asyncTable, DatabaseAPI]

class _Where:
    def __getitem__(self, index):
        return index.text

where = _Where()

class Clause:
    def __init__(self, text):
        self.text= text

    def __and__(self, other):
        return Clause(f"{self.text} AND {other.text}")

    def __or__(self, other):
        return Clause(f"{self.text} OR {other.text}")

class Column:
    def __hash__(self):
        return id(self)

    def __init__(self, column_name, table_obj, db_obj):
        self.column_name = column_name
        self.table_obj = table_obj
        self.db_obj = db_obj

    def parse(self, other):
        if isinstance(other, types.NoneType):
            return None
        if isinstance(other, str):
            other = other.replace('"', '""')
            other = f'"{other}"'
        elif isinstance(other, (date, time, datetime)):
            other = f'"{str(other)}"'
        return other

    def __eq__(self, other):
        other = self.parse(other)
        if isinstance(other, types.NoneType):
            return Clause(f"({self.column_name} IS NULL)")
        return Clause(f"({self.column_name} = {other})")

    def __ne__(self, other):
        other = self.parse(other)
        if isinstance(other, types.NoneType):
            return Clause(f"({self.column_name} IS NOT NULL)")
        return Clause(f"({self.column_name} != {other})")

    def __lt__(self, other):
        other = self.parse(other)
        return Clause(f"({self.column_name} < {other})")

    def __gt__(self, other):
        other = self.parse(other)
        return Clause(f"({self.column_name} > {other})")

    def __le__(self, other):
        other = self.parse(other)
        return Clause(f"({self.column_name} <= {other})")

    def __ge__(self, other):
        other = self.parse(other)
        return Clause(f"({self.column_name} >= {other})")

class TableMySQL:
    def _check_schema_exists(self):
        cur = self.db_obj.conn.cursor()
        cur.execute("""
            SELECT TABLE_NAME 
            FROM information_schema.tables 
            WHERE table_schema = %s AND table_name = %s;
        """, (self.db_obj._init_args["database"], self.table_name))
        exists = cur.fetchone() is not None
        cur.close()
        return exists

    def Check(self, where=None, fetch=None, columns=['*']):
        # Normalize column names
        if isinstance(columns, list):
            columns = [
                column.column_name if not isinstance(column, str) else column
                for column in columns
            ]
        
        # Build SQL parts
        table = f"`{self.table_name}`"
        W = f"WHERE {where}" if where else ""
        L = f"LIMIT {fetch}" if isinstance(fetch, int) else ""
        C = ", ".join(f"`{col}`" if col != '*' else '*' for col in columns)

        # Execute query
        cur = self.db_obj.conn.cursor()
        cur.execute(f"SELECT {C} FROM {table} {W} {L};")

        # Decide how to fetch
        if fetch:
            response = cur.fetchall()
            cur.close()
            return response
        else:
            response = cur.fetchone()
            cur.fetchall()  # Drain the cursor
            cur.close()
            return bool(response)
    
    def Insert(self, *dict_input, **data):
        if not data and dict_input:
            data = dict_input[0]

        table = f"`{self.table_name}`"
        data_keys = []

        for key in data.keys():
            if isinstance(key, Column):
                data_keys.append(f"`{key.column_name}`")
            elif isinstance(key, str):
                data_keys.append(f"`{key}`")
            else:
                raise TypeError(f"Invalid column type {type(key).__name__}")

        placeholders = ", ".join(["%s"] * len(data))
        columns_str = ", ".join(data_keys)
        values = list(data.values())

        cur = self.db_obj.conn.cursor()
        try:
            cur.execute(
                f"INSERT INTO {table} ({columns_str}) VALUES ({placeholders});",
                tuple(values)
            )
            self.db_obj.conn.commit()
            inserted_id = cur.lastrowid
            cur.close()
            return inserted_id
        except Exception:
            cur.close()
            return False
    
    def Delete(self, where=None):
        table = f"`{self.table_name}`"
        if where:
            query = f"DELETE FROM {table} WHERE {where};"
        else:
            query = f"DELETE FROM {table};"

        cur = self.db_obj.conn.cursor()
        cur.execute(query)
        self.db_obj.conn.commit()
        cur.close()

    def Update(self, where=None, **data):
        # Normalize column keys
        data = {
            (key.column_name if isinstance(key, Column) else key): val
            for key, val in data.items()
        }

        table = f"`{self.table_name}`"
        set_clauses = []
        params = []

        for key, val in data.items():
            set_clauses.append(f"`{key}` = %s")
            params.append(val)

        set_clause_str = ", ".join(set_clauses)
        query = f"UPDATE {table} SET {set_clause_str}"

        if where:
            query += f" WHERE {where}"

        query += ";"

        cur = self.db_obj.conn.cursor()
        cur.execute(query, tuple(params))
        self.db_obj.conn.commit()
        cur.close()
    
    def ExecScript(self, script: str, params: tuple) -> bool:
        try:
            cur = self.db_obj.conn.cursor()
            cur.execute(script, params)
            self.db_obj.conn.commit()
            cur.close()
            return True
        except Exception as e:
            # Optional: log or print(e) for debugging
            return False
    
    def initiate_columns(self):
        for col in self.fields:
            self.columns[col] = Column(col, self, self.db_obj)
            if col not in dir(self):
                setattr(self, col, self.columns[col])
            else:
                raise NameError(f"NameConflict: Column ({col})")
    
    def __init__(self, table_name, fields, db_obj):
        self.columns = dict()
        self.table_name = table_name
        self.fields = fields
        self.db_obj:DatabaseAPI = db_obj
        self.initiate_columns()

class TableSQLite:
    def _check_schema_exists(self):
        cur = self.db_obj.conn.cursor()
        cur.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name=?;
        """, (self.table_name,))
        exists = cur.fetchone() is not None
        cur.close()
        return exists

    def Check(self, where=None, fetch=None, columns=['*']):
        if isinstance(columns, list):
            columns = [(column.column_name if not isinstance(column, str) else column) for column in columns]
        table = self.table_name
        W = ''
        if where: W = f'WHERE {where}'
        if isinstance(fetch, int): L = f'LIMIT {fetch}'
        else: L = ''
        cur = self.db_obj.conn.cursor()
        cur.execute(f'''SELECT {str(columns)[1:-1].replace('"', '').replace("'", '')} FROM {table}\n{W}\n{L};''')
        self.db_obj.conn.commit()
        if fetch: response = cur.fetchall(); cur.close(); return response 
        else: response = bool(cur.fetchone()); cur.fetchall(); cur.close(); return response
    
    def Insert(self, *dict_input, **data):
        if not data and dict_input:
            data = dict_input[0]
        table = self.table_name
        data_keys = []
        for data_ in data.keys():
            if isinstance(data_, Column):
                data_keys.append(data_.column_name)
            elif isinstance(data_, str):
                data_keys.append(data_)
            else: raise TypeError(
                f"Invalid column type {type(data_).__name__}"
            )
        key = (str(list(data_keys)).replace('"', '')).replace("'", '')
        val = list(data.values())
        cur = self.db_obj.conn.cursor()
        try:
            cur.execute(f'''INSERT INTO {table} ({key[1:-1]})\nVALUES ({("?,"*len(val))[:-1]});''', tuple(val))
            self.db_obj.conn.commit()
            inserted_id = cur.lastrowid
            cur.close()
            return inserted_id
        except:
            return False

    def Delete(self, where=None):
        table = self.table_name
        if where: query = f'DELETE FROM {table} WHERE {where};'
        else: query = f'DELETE FROM {table};'
        cur = self.db_obj.conn.cursor()
        cur.execute(query)
        self.db_obj.conn.commit()
        cur.close()

    def Update(self, where=None, **data):
        data = {(key.column_name if isinstance(key, Column) else key): val for key, val in data.items()}
        table = self.table_name
        S = 'SET'; W = ''; params = []
        for key in data:
            val = data[key]
            params.append(val)
            S+=f" {key}=?,"
        if where:
            W = f'WHERE {where}'
        query = f"""UPDATE {table}\n{S[:-1]}\n{W};"""
        cur = self.db_obj.conn.cursor()
        cur.execute(query, tuple(params))
        self.db_obj.conn.commit()
        cur.close()
    
    def ExecScript(self, script:str, params:tuple) -> bool:
        try:
            cur = self.db_obj.conn.cursor()
            cur.execute(script, params)
            self.db_obj.conn.commit()
            cur.close()
            return True
        except:
            return False

    def initiate_columns(self):
        for col in self.fields:
            self.columns[col] = Column(col, self, self.db_obj)
            if col not in dir(self):
                setattr(self, col, self.columns[col])
            else: raise NameError(
                f"NameConflict: Column ({col})"
            )

    def __init__(self, table_name, fields, db_obj):
        self.columns = dict()
        self.table_name = table_name
        self.fields = fields
        self.db_obj:DatabaseAPI = db_obj
        self.initiate_columns()

class AsyncTableSQLite(TableSQLite):
    async def _check_schema_exists(self):
        conn:aiosqlite.Connection = await self.db_obj.pool.get_connection()
        try:
            async with conn.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name=?;
            """, (self.table_name,)) as cursor:
                exists = await cursor.fetchone() is not None
        except Exception as e:
            logging.getLogger("main_logger").error(f"[CloudStorageServer-RBAC] Failed to check if table '{self.table_name}' exists - error: {e} - traceback: {traceback.format_exc()}")
            exists = None
            raise RuntimeError(
                f"[CloudStorageServer-RBAC] Unexpected error occurred while checking if table '{self.table_name}' exists."
            ) from e
        finally:
            await self.db_obj.pool.release_connection(conn)
            return exists

    async def Check(self, where=None, fetch=None, columns=['*']):
        if isinstance(columns, list):
            columns = [(column.column_name if not isinstance(column, str) else column) for column in columns]
        table = self.table_name
        W = ''
        if where: W = f'WHERE {where}'
        if isinstance(fetch, int): L = f'LIMIT {fetch}'
        else: L = ''
        conn:aiosqlite.Connection = await self.db_obj.pool.get_connection()
        async with conn.cursor() as cursor:
            try:
                await cursor.execute(f"""SELECT {', '.join(columns)} FROM {table}\n{W}\n{L};""")
                if fetch:
                    response = await cursor.fetchall()
                    return response 
                else:
                    response = bool(await cursor.fetchone())
                    return response
            finally:
                await self.db_obj.pool.release_connection(conn)
    
    async def Insert(self, *dict_input, **data):
        if not data and dict_input:
            data = dict_input[0]
        table = self.table_name
        data_keys = []
        for data_ in data.keys():
            if isinstance(data_, Column):
                data_keys.append(data_.column_name)
            elif isinstance(data_, str):
                data_keys.append(data_)
            else: raise TypeError(
                f"Invalid column type {type(data_).__name__}"
            )
        key = ", ".join(data_keys)
        val = list(data.values())
        conn:aiosqlite.Connection = await self.db_obj.pool.get_connection()
        async with conn.cursor() as cursor:
            try:
                await cursor.execute(f"""INSERT INTO {table} ({key}) VALUES ({", ".join(['?'] * len(val))});""", tuple(val))
                await conn.commit()
                inserted_id = cursor.lastrowid
                return inserted_id
            except aiosqlite.Error:
                return False  # Insertion failed
            finally:
                await self.db_obj.pool.release_connection(conn)

    async def Delete(self, where=None):
        table = self.table_name
        if where: query = f'DELETE FROM {table} WHERE {where};'
        else: query = f'DELETE FROM {table};'
        conn:aiosqlite.Connection = await self.db_obj.pool.get_connection()
        async with conn.cursor() as cursor:
            try:
                await cursor.execute(query)
                await conn.commit()
                return True
            except aiosqlite.Error:
                return False # signal error
            finally:
                await self.db_obj.pool.release_connection(conn)

    async def Update(self, where=None, **data):
        data = {(key.column_name if isinstance(key, Column) else key): val for key, val in data.items()}
        table = self.table_name
        set_clauses = [f"{key} = ?" for key in data]
        params = list(data.values())
        S = ", ".join(set_clauses)
        W = f'WHERE {where}' if where else ''
        query = f"UPDATE {table} SET {S} {W};"
        conn:aiosqlite.Connection = await self.db_obj.pool.get_connection()
        async with conn.cursor() as cursor:
            try:
                await cursor.execute(query, tuple(params))
                await conn.commit()
            except aiosqlite.Error:
                return False # signal error
            finally:
                await self.db_obj.pool.release_connection(conn)
    
    async def ExecScript(self, script:str, params:tuple) -> bool:
        conn:aiosqlite.Connection = await self.db_obj.pool.get_connection()
        async with conn.cursor() as cursor:
            try:
                await cursor.execute(script, params)
                await conn.commit()
                inserted_id = cursor.lastrowid
                return inserted_id
            except aiosqlite.Error as e:
                return False  # Insertion failed
            finally:
                await self.db_obj.pool.release_connection(conn)

# Scalable Connection Pooling Mechanism [SQLite Deprecated]
class ConnectionPool: # abstract class
    async def init_pool(self): ...
    async def get_connection(self): ...
    async def release_connection(self, conn): ...
    async def close_pool(self): ...

class SQLiteConnectionPool(ConnectionPool):
    def __init__(self, db_file, pool_size=10):
        self.db_file = db_file
        self.pool_size = pool_size
        self.pool = Queue(maxsize=pool_size)
        self.temp_conns = []
        self.active_connections = 0

    async def init_pool(self):
        for _ in range(self.pool_size):
            conn = await aiosqlite.connect(self.db_file, check_same_thread=False)
            await self.pool.put(conn)

    async def get_connection(self):
        if self.pool.empty() and self.active_connections < self.pool_size:
            # create a short-lived connection if none are available
            conn = await aiosqlite.connect(self.db_file, check_same_thread=False)
            self.temp_conns.append(conn)
            self.active_connections += 1
        else:
            conn = await self.pool.get()
        return conn

    async def release_connection(self, conn:aiosqlite.Connection):
        if self.pool.full() and (conn in self.temp_conns):
            self.temp_conns.remove(conn)
            await conn.close()
            self.active_connections -= 1
        else:
            await self.pool.put(conn)

    async def close_pool(self):
        while not self.pool.empty():
            conn = await self.pool.get()
            await conn.close()

# High-Level Database APIs
class DatabaseAPI: # abstract class
    DBMS:str
    is_async:bool
    database_path:pathlib.Path
    _init_args:dict
    # CURD methods
    def Check(self, where=None, fetch=None, columns=['*']): ...
    def Insert(self, **data): ...
    def Update(self, where=None, **data): ...
    def Delete(self, where=None): ...
    # Raw SQL execution
    def ExecScript(self, script:str, params:tuple) -> bool: ...
    # Database initiation
    def extract_tables(self): ...
    def extract_fields(self): ...
    def initiate_tables(self): ...
    # refresh database for structural and relational changes
    def refresh(self):
        return  self.__class__(*self._init_args)
    # async connection pool (SQLite-specific)
    pool:SQLiteConnectionPool = None # none for sycn APIs
    # sycn connection
    conn:sqlite3.Connection = None # none for async APIs

class SQLiteDatabase(DatabaseAPI):
    is_async = False
    DBMS = 'SQLite'
    def extract_tables(self):
        self.cur.execute("SELECT name\nFROM sqlite_master\nWHERE type = 'table';")
        self.tables_names = [table_name[0] for table_name in self.cur.fetchall()]

    def extract_fields(self):
        for table in self.tables_names:
            self.cur.execute(f"PRAGMA table_info({table});")
            self.fields[table] = [field[1] for field in self.cur.fetchall()]

    def initiate_tables(self):
        for table in self.tables_names:
            self.tables[table] = TableSQLite(table, self.fields[table], self)
            if table not in dir(self):
                setattr(self, table, self.tables[table])
            else: raise NameError(
                f"NameConflict: Table ({table})"
            )

    def __init__(self, database_path:pathlib.Path):
        self._init_args = {
            database_path: database_path
        }
        # vars
        self.database_path = database_path
        self.fields = dict()
        self.tables = dict()
        self.where = _Where()
        # connect to database
        self.conn = sqlite3.connect(database_path, check_same_thread=False)
        self.cur = self.conn.cursor()
        self.extract_tables()
        self.extract_fields()
        self.cur.close()
        self.initiate_tables()

class MySQLDatabase(DatabaseAPI):
    is_async = False
    DBMS = 'MySQL'

    def extract_tables(self):
        self.cur.execute("SHOW TABLES;")
        self.tables_names = [table_name[0] for table_name in self.cur.fetchall()]

    def extract_fields(self):
        for table in self.tables_names:
            self.cur.execute(f"DESCRIBE `{table}`;")
            self.fields[table] = [field[0] for field in self.cur.fetchall()]

    def initiate_tables(self):
        for table in self.tables_names:
            self.tables[table] = TableMySQL(table, self.fields[table], self)
            if table not in dir(self):
                setattr(self, table, self.tables[table])
            else:
                raise NameError(f"NameConflict: Table ({table})")
    
    def config(host: str, user: str, password: str, database: str):
        CREDENTIALS.update({
            "host": host,
            "user": user,
            "password": password,
            "database": database
        })

    def __init__(self):
        # vars
        self.fields = dict()
        self.tables = dict()
        self.where = _Where()
        # connect to database
        self.conn = mysql.connector.connect(**CREDENTIALS)
        self.cur = self.conn.cursor()
        self.extract_tables()
        self.extract_fields()
        self.cur.close()
        self.initiate_tables()

class AsyncSQLiteDatabase(DatabaseAPI):
    # Deprecated: SQLite is not quite good for async operations
    is_async = True
    DBMS = 'SQLite'
    pool_size = 5
    def extract_tables(self):
        self.cursor.execute("SELECT name FROM sqlite_master WHERE type = 'table';")
        self.tables_names = [table_name[0] for table_name in self.cursor.fetchall()]

    def extract_fields(self):
        for table in self.tables_names:
            self.cursor.execute(f"PRAGMA table_info({table});")
            self.fields[table] = [field[1] for field in self.cursor.fetchall()]

    def initiate_tables(self):
        for table in self.tables_names:
            self.tables[table] = AsyncTableSQLite(table, self.fields[table], self)
            if table not in dir(self):
                setattr(self, table, self.tables[table])
            else: raise NameError(
                f"NameConflict: Table ({table})"
            )
    
    async def refresh(self):
        await self.pool.close_pool()
        return super().refresh()

    def __init__(self, database_path:pathlib.Path, pool_size:int=pool_size):
        self._init_args = {
            database_path: database_path,
            pool_size: pool_size
        }
        # vars
        self.database_path = database_path
        self.fields = dict()
        self.tables = dict()
        self.where = _Where()
        # startup connection
        self.startup_conn = sqlite3.connect(database_path)
        self.cursor = self.startup_conn.cursor()
        self.extract_tables()
        self.extract_fields()
        self.cursor.close()
        self.startup_conn.close()
        # connection pool
        self.pool = SQLiteConnectionPool(
            db_file=database_path,
            pool_size=pool_size
        )
        self.initiate_tables()
