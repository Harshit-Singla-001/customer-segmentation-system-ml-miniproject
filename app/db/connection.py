import pymysql
from pymysql.cursors import DictCursor
from config import Config

def get_db_connection(with_database=True):
    """
    Returns a PyMySQL database connection.
    If with_database is False, connects without selecting a specific database
    (useful for database creation scripts).
    """
    connection = pymysql.connect(
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        database=Config.DB_NAME if with_database else None,
        cursorclass=DictCursor,
        autocommit=False
    )
    return connection

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
    Reads sql/schema.sql and initializes the database tables and seed data if database exists.
    """
    import os
    sql_file_path = os.path.join(Config.BASE_DIR, 'sql', 'schema.sql')
    if not os.path.exists(sql_file_path):
        return False, "schema.sql file not found."
    
    try:
        # First ensure DB exists
        conn = get_db_connection(with_database=False)
        with conn.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{Config.DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
        conn.commit()
        conn.close()

        # Now execute schema script statements
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
