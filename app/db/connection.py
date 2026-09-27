import os
import re
import sqlite3
from datetime import datetime
from config import Config

_CACHED_RESOLVED_HOSTS = {}

def resolve_host(hostname):
    if not hostname or hostname in ('localhost', '127.0.0.1'):
        return hostname
    if hostname in _CACHED_RESOLVED_HOSTS:
        return _CACHED_RESOLVED_HOSTS[hostname]

    import socket
    try:
        ip = socket.gethostbyname(hostname)
        _CACHED_RESOLVED_HOSTS[hostname] = ip
        return ip
    except socket.gaierror:
        import subprocess
        try:
            cmd_out = subprocess.check_output(f"nslookup {hostname} 8.8.8.8", shell=True, text=True, stderr=subprocess.DEVNULL)
            ips = re.findall(r"Addresses?:\s*([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)", cmd_out)
            if ips:
                _CACHED_RESOLVED_HOSTS[hostname] = ips[0]
                return ips[0]
        except Exception:
            pass
        _CACHED_RESOLVED_HOSTS[hostname] = hostname
        return hostname


# ── SQLite Compatibility Layer ─────────────────────────────────────────────

def dict_factory(cursor, row):
    """Row factory that returns pure Python dictionaries with .get() support."""
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


class SQLiteCursorWrapper:
    """
    Wraps sqlite3.Cursor to provide compatibility with PyMySQL's DictCursor:
    - Context manager support (`with conn.cursor() as cursor:`)
    - Automatic translation of `%s` placeholders to `?`
    - Automatic translation of `INSERT IGNORE` to `INSERT OR IGNORE`
    - `cursor.lastrowid` preserved
    - Returns dictionary rows with `.get()` method
    """
    def __init__(self, cursor):
        self._cursor = cursor

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._cursor.close()

    @property
    def lastrowid(self):
        return self._cursor.lastrowid

    @property
    def rowcount(self):
        return self._cursor.rowcount

    @property
    def description(self):
        return self._cursor.description

    @staticmethod
    def _adapt_sql(query):
        if not query:
            return query
        # Translate MySQL INSERT IGNORE -> SQLite INSERT OR IGNORE
        q = re.sub(r'\bINSERT\s+IGNORE\s+INTO\b', 'INSERT OR IGNORE INTO', query, flags=re.IGNORECASE)
        # Translate %s parameter placeholders -> SQLite ?
        q = re.sub(r'(?<!%)%s', '?', q).replace('%%', '%')
        return q

    def execute(self, query, params=None):
        adapted_sql = self._adapt_sql(query)
        if params is None:
            return self._cursor.execute(adapted_sql)
        return self._cursor.execute(adapted_sql, params)

    def executemany(self, query, seq_of_params):
        adapted_sql = self._adapt_sql(query)
        return self._cursor.executemany(adapted_sql, seq_of_params)

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchall(self):
        return self._cursor.fetchall()

    def fetchmany(self, size=None):
        return self._cursor.fetchmany(size) if size is not None else self._cursor.fetchmany()

    def close(self):
        return self._cursor.close()


class SQLiteConnectionWrapper:
    """
    Wraps sqlite3.Connection to provide a unified interface with PyMySQL connections.
    """
    def __init__(self, conn):
        self._conn = conn

    def cursor(self):
        return SQLiteCursorWrapper(self._conn.cursor())

    def commit(self):
        return self._conn.commit()

    def rollback(self):
        return self._conn.rollback()

    def close(self):
        return self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self._conn.rollback()
        else:
            self._conn.commit()


# ── Database Connection Factory ────────────────────────────────────────────

def get_db_connection(with_database=True):
    """
    Returns a database connection:
    - If Config.DB_TYPE == 'sqlite' (default), returns SQLiteConnectionWrapper.
    - If Config.DB_TYPE == 'mysql', returns PyMySQL DictCursor connection.
    """
    if Config.DB_TYPE == 'sqlite':
        instance_dir = os.path.dirname(Config.SQLITE_PATH)
        os.makedirs(instance_dir, exist_ok=True)
        
        raw_conn = sqlite3.connect(Config.SQLITE_PATH, timeout=30.0, check_same_thread=False)
        raw_conn.row_factory = dict_factory
        
        # Enable foreign keys
        raw_conn.execute("PRAGMA foreign_keys = ON;")
        
        # Register MySQL-compatible SQL functions in SQLite
        raw_conn.create_function("GREATEST", -1, max)
        raw_conn.create_function("LEAST", -1, min)
        raw_conn.create_function("NOW", 0, lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        
        return SQLiteConnectionWrapper(raw_conn)
    
    # Fallback to MySQL
    import pymysql
    from pymysql.cursors import DictCursor

    target_host = resolve_host(Config.DB_HOST)
    conn_kwargs = {
        'host': target_host,
        'port': Config.DB_PORT,
        'user': Config.DB_USER,
        'password': Config.DB_PASSWORD,
        'cursorclass': DictCursor,
        'autocommit': False,
        'connect_timeout': 10
    }
    if with_database and Config.DB_NAME:
        conn_kwargs['database'] = Config.DB_NAME

    if 'aivencloud.com' in Config.DB_HOST.lower() or os.environ.get('DB_SSL', 'false').lower() == 'true':
        import ssl
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE
        conn_kwargs['ssl'] = ssl_ctx

    return pymysql.connect(**conn_kwargs)


def execute_query(query, params=None, fetch_all=False, fetch_one=False, commit=False):
    """
    Executes a SQL query safely and handles connection lifecycle.
    """
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute(query, params or ())
            result = None
            if fetch_all:
                result = cursor.fetchall()
            elif fetch_one:
                result = cursor.fetchone()
            elif cursor.lastrowid:
                result = cursor.lastrowid
            
            if commit:
                connection.commit()
            return result
    except Exception as e:
        if connection and commit:
            connection.rollback()
        raise e
    finally:
        if connection:
            connection.close()


def init_db():
    """
    Initializes database tables and seed data using SQLite or MySQL schema.
    """
    if Config.DB_TYPE == 'sqlite':
        sql_file_path = os.path.join(Config.BASE_DIR, 'sql', 'schema_sqlite.sql')
        if not os.path.exists(sql_file_path):
            sql_file_path = os.path.join(Config.BASE_DIR, 'sql', 'schema.sql')
        
        if not os.path.exists(sql_file_path):
            return False, "Schema SQL file not found."

        try:
            instance_dir = os.path.dirname(Config.SQLITE_PATH)
            os.makedirs(instance_dir, exist_ok=True)
            
            with open(sql_file_path, 'r', encoding='utf-8') as f:
                sql_script = f.read()

            raw_conn = sqlite3.connect(Config.SQLITE_PATH, timeout=30.0)
            raw_conn.execute("PRAGMA foreign_keys = OFF;")
            raw_conn.executescript(sql_script)
            raw_conn.execute("PRAGMA foreign_keys = ON;")
            raw_conn.commit()
            raw_conn.close()
            return True, "SQLite database initialized successfully."
        except Exception as e:
            return False, str(e)

    # MySQL initialization
    sql_file_path = os.path.join(Config.BASE_DIR, 'sql', 'schema.sql')
    if not os.path.exists(sql_file_path):
        return False, "schema.sql file not found."
    
    try:
        try:
            conn = get_db_connection(with_database=False)
            with conn.cursor() as cursor:
                cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{Config.DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
            conn.commit()
            conn.close()
        except Exception:
            pass

        conn = get_db_connection(with_database=True)
        with conn.cursor() as cursor:
            with open(sql_file_path, 'r', encoding='utf-8') as f:
                sql_script = f.read()
            
            statements = [s.strip() for s in sql_script.split(';') if s.strip()]
            for statement in statements:
                if statement.lower().startswith("create database") or statement.lower().startswith("use "):
                    continue
                cursor.execute(statement)
        conn.commit()
        conn.close()
        return True, "Database initialized successfully."
    except Exception as e:
        return False, str(e)


def is_sqlite_data_inserted():
    """
    Ultra-fast conditional check (takes <1ms) to verify if the SQLite DB file exists
    and already has customers and products data inserted.
    """
    if not os.path.exists(Config.SQLITE_PATH):
        return False
    if os.path.getsize(Config.SQLITE_PATH) < 4096:
        return False
    try:
        raw_conn = sqlite3.connect(Config.SQLITE_PATH, timeout=5.0)
        cur = raw_conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('customers', 'products', 'admins');")
        tables = [r[0] for r in cur.fetchall()]
        if len(tables) < 3:
            raw_conn.close()
            return False
        cur.execute("SELECT COUNT(*) FROM customers;")
        c_count = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM products;")
        p_count = cur.fetchone()[0]
        raw_conn.close()
        return c_count > 0 and p_count > 0
    except Exception:
        return False


def check_and_auto_import_db():
    """
    Checks if the database is already initialized and populated.
    - In SQLite mode: Uses an instant conditional check (<1ms) to see if data is already inserted.
      If data exists, it immediately skips without any delay.
      If not inserted, initializes schema and auto-imports the CSV dataset.
    - In MySQL mode: Checks fingerprint and auto-imports if changed.
    """
    if Config.DB_TYPE == 'sqlite':
        if is_sqlite_data_inserted():
            try:
                res = execute_query("SELECT COUNT(*) as cnt FROM clusters", fetch_one=True)
                if not res or res.get('cnt', 0) == 0:
                    from app.ml.clustering import train_kmeans_model
                    train_kmeans_model(save=True)
            except Exception:
                pass
            print("[AUTO-DB] SQLite database verified with existing data. Ready instantly (<1ms).")
            return True, "SQLite database ready with existing data."

        print("[AUTO-DB] SQLite database file not found or empty. Initializing schema and importing sample dataset...")
        ok, msg = init_db()
        if not ok:
            print(f"[AUTO-DB] Error initializing SQLite schema: {msg}")
            return False, msg

        try:
            from scripts.import_to_db import import_data
            import_data()
            from app.ml.clustering import train_kmeans_model
            train_kmeans_model(save=True)
            print("[AUTO-DB] Sample dataset auto-imported and initial K-Means clusters generated successfully!")
            return True, "Auto-imported CSV data and trained clusters."
        except Exception as e:
            print(f"[AUTO-DB] Error importing CSV data into SQLite: {e}")
            return False, str(e)

    # MySQL Mode
    instance_dir = os.path.join(Config.BASE_DIR, 'instance')
    os.makedirs(instance_dir, exist_ok=True)
    fp_file = os.path.join(instance_dir, 'db_fingerprint.txt')

    current_fp = f"{Config.DB_HOST}:{Config.DB_PORT}/{Config.DB_NAME}@{Config.DB_USER}"
    saved_fp = ""
    if os.path.exists(fp_file):
        try:
            with open(fp_file, 'r', encoding='utf-8') as f:
                saved_fp = f.read().strip()
        except Exception:
            saved_fp = ""

    needs_import = (current_fp != saved_fp)

    if not needs_import:
        try:
            res = execute_query("SELECT COUNT(*) as count FROM customers", fetch_one=True)
            if not res or res.get('count', 0) == 0:
                needs_import = True
        except Exception:
            needs_import = True

    if needs_import:
        print(f"[AUTO-DB] New or uninitialized database connection detected ({current_fp}). Initializing schema and importing CSV sample dataset...")
        ok, msg = init_db()
        if not ok:
            print(f"[AUTO-DB] Error initializing DB schema: {msg}")
            return False, msg

        try:
            from scripts.import_to_db import import_data
            import_data()
            with open(fp_file, 'w', encoding='utf-8') as f:
                f.write(current_fp)
            print("[AUTO-DB] Sample dataset auto-imported successfully into the new database!")
            return True, "Auto-imported CSV data into new DB."
        except Exception as e:
            print(f"[AUTO-DB] Error importing CSV data: {e}")
            return False, str(e)

    return True, "Database link unchanged."
