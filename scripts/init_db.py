import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config
from app.db.connection import init_db as app_init_db, get_db_connection

def init_db():
    print(f"Initializing database for engine: {Config.DB_TYPE.upper()}...")
    success, msg = app_init_db()
    if not success:
        print(f"Error initializing DB: {msg}")
        return

    conn = get_db_connection(with_database=True)
    cursor = conn.cursor()
    if Config.DB_TYPE == 'sqlite':
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
        tables = cursor.fetchall()
        print(f"Tables in SQLite database ({Config.SQLITE_PATH}):")
        for t in tables:
            print(" -", t['name'])
    else:
        cursor.execute('SHOW TABLES;')
        tables = cursor.fetchall()
        print("Tables in MySQL database:")
        for t in tables:
            print(" -", list(t.values())[0])
    conn.close()
    print("Database initialization completed successfully.")

if __name__ == "__main__":
    init_db()
