from datetime import date, time, datetime
import sqlite3, aiosqlite
from asyncio import Queue
import types

class Where:
    def __getitem__(self, index):
        return index.text

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

class Table:
    def Check(self, where=None, fetch=None, columns=['*']):
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
    
    def Insert(self, data):
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
        except: return False

    def Delete(self, where=None):
        table = self.table_name
        if where: query = f'DELETE FROM {table} WHERE {where};'
        else: query = f'DELETE FROM {table};'
        cur = self.db_obj.conn.cursor()
        cur.execute(query)
        self.db_obj.conn.commit()
        cur.close()

    def Update(self, data:dict, where=None):
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
        self.db_obj = db_obj
        self.initiate_columns()

class AsyncTable(Table):
    async def Check(self, where=None, fetch=None, columns=['*']):
        table = self.table_name
        W = ''
        if where: W = f'WHERE {where}'
        if isinstance(fetch, int): L = f'LIMIT {fetch}'
        else: L = ''
        conn = await self.db_obj.pool.get_connection()
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
    
    async def Insert(self, data):
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
        conn = await self.db_obj.pool.get_connection()
        async with conn.cursor() as cursor:
            try:
                await cursor.execute(f"""INSERT INTO {table} ({key}) VALUES ({", ".join(['?'] * len(val))});""", tuple(val))
                await conn.commit()
                inserted_id = cursor.lastrowid
                return inserted_id
            except sqlite3.DatabaseError as e:
                print(f"Error during insert: {e}")
                return False  # Insertion failed
            finally:
                await self.db_obj.pool.release_connection(conn)

    async def Delete(self, where=None):
        table = self.table_name
        if where: query = f'DELETE FROM {table} WHERE {where};'
        else: query = f'DELETE FROM {table};'
        conn = await self.db_obj.pool.get_connection()
        async with conn.cursor() as cursor:
            try:
                await cursor.execute(query)
                await conn.commit()
            finally:
                await self.db_obj.pool.release_connection(conn)

    async def Update(self, data:dict, where=None):
        data = {(key.column_name if isinstance(key, Column) else key): val for key, val in data.items()}
        table = self.table_name
        set_clauses = [f"{key} = ?" for key in data]
        params = list(data.values())
        S = ", ".join(set_clauses)
        W = f'WHERE {where}' if where else ''
        query = f"UPDATE {table} SET {S} {W};"
        conn = await self.db_obj.pool.get_connection()
        async with conn.cursor() as cursor:
            try:
                await cursor.execute(query, tuple(params))
                await conn.commit()
            finally:
                await self.db_obj.pool.release_connection(conn)

class SQLiteDatabase:
    def extract_tables(self):
        self.cur.execute("SELECT name\nFROM sqlite_master\nWHERE type = 'table';")
        self.tables_names = [table_name[0] for table_name in self.cur.fetchall()]

    def extract_fields(self):
        for table in self.tables_names:
            self.cur.execute(f"PRAGMA table_info({table});")
            self.fields[table] = [field[1] for field in self.cur.fetchall()]

    def initiate_tables(self):
        for table in self.tables_names:
            self.tables[table] = Table(table, self.fields[table], self)
            if table not in dir(self):
                setattr(self, table, self.tables[table])
            else: raise NameError(
                f"NameConflict: Table ({table})"
            )

    def __init__(self, database_path):
        self.database_path = database_path
        self.fields = dict()
        self.tables = dict()
        self.where = Where()
        # connect to database
        self.conn = sqlite3.connect(database_path, check_same_thread=False)
        self.cur = self.conn.cursor()
        self.extract_tables()
        self.extract_fields()
        self.cur.close()
        self.initiate_tables()

class SQLiteConnectionPool:
    def __init__(self, db_file, pool_size=10):
        self.db_file = db_file
        self.pool_size = pool_size
        self.pool = Queue(maxsize=pool_size)
        self.active_connections = 0

    async def init_pool(self):
        for _ in range(self.pool_size):
            conn = await aiosqlite.connect(self.db_file, check_same_thread=False)
            await self.pool.put(conn)

    async def get_connection(self):
        if self.pool.empty() and self.active_connections < self.pool_size:
            # create a short-lived connection if none are available
            conn = await aiosqlite.connect(self.db_file, check_same_thread=False)
            self.active_connections += 1
        else:
            conn = await self.pool.get()
        return conn

    async def release_connection(self, conn):
        if self.pool.full(): # for short-lived connections
            await conn.close()
            self.active_connections -= 1
        else:
            await self.pool.put(conn)

    async def close_pool(self):
        while not self.pool.empty():
            conn = await self.pool.get()
            await conn.close()

class AsyncSQLiteDatabase:
    def extract_tables(self):
        self.cursor.execute("SELECT name FROM sqlite_master WHERE type = 'table';")
        self.tables_names = [table_name[0] for table_name in self.cursor.fetchall()]

    def extract_fields(self):
        for table in self.tables_names:
            self.cursor.execute(f"PRAGMA table_info({table});")
            self.fields[table] = [field[1] for field in self.cursor.fetchall()]

    def initiate_tables(self):
        for table in self.tables_names:
            self.tables[table] = AsyncTable(table, self.fields[table], self)
            if table not in dir(self):
                setattr(self, table, self.tables[table])
            else: raise NameError(
                f"NameConflict: Table ({table})"
            )

    def __init__(self, database_path, pool_size=5):
        self.database_path = database_path
        self.fields = dict()
        self.tables = dict()
        self.where = Where()
        # startup connection
        self.startup_conn = sqlite3.connect(database_path, check_same_thread=False)
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
