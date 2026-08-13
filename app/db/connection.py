import os
import pymysql
from pymysql.cursors import DictCursor
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
        import subprocess, re
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

def get_db_connection(with_database=True):
    """
    Returns a PyMySQL database connection.
    Supports local MySQL as well as SSL-enforced Cloud MySQL (e.g. Aiven).
    """
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

    # Enable SSL for cloud hosts (e.g. aivencloud.com) or when explicitly configured
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
    Reads sql/schema.sql and initializes the database tables and seed data.
    """
    sql_file_path = os.path.join(Config.BASE_DIR, 'sql', 'schema.sql')
    if not os.path.exists(sql_file_path):
        return False, "schema.sql file not found."
    
    try:
        # Try to ensure DB exists if permissions allow
        try:
            conn = get_db_connection(with_database=False)
            with conn.cursor() as cursor:
                cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{Config.DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
            conn.commit()
            conn.close()
        except Exception:
            pass  # In cloud environments like Aiven defaultdb is already allocated

        # Execute schema script statements
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


def check_and_auto_import_db():
    """
    Checks if the database host/URI parameter has changed or if the database is uninitialized.
    If so, automatically creates schema and imports sample CSV dataset into the target MySQL database.
    """
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

    # If fingerprint matches, verify if tables actually exist and have data
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

