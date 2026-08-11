import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.db.connection import get_db_connection


def init_db():
    conn = get_db_connection(with_database=True)
    cursor = conn.cursor()
    with open('sql/schema.sql', 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    # Execute statements split by semicolon
    statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
    for stmt in statements:
        try:
            cursor.execute(stmt)
        except Exception as e:
            print(f"Executing statement warning: {e}")
    conn.commit()
    
    cursor.execute('SHOW TABLES;')
    tables = cursor.fetchall()
    print("Tables in customer_segmentation_db:")
    for t in tables:
        print(" -", list(t.values())[0])
    conn.close()

if __name__ == "__main__":
    init_db()
