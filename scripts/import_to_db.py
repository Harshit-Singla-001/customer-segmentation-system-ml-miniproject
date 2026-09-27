import sys
import os
import re
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config
from app.db.connection import get_db_connection

def parse_id(val):
    """Extract integer from string IDs like 'C00001', 'P0001', 'PUR000001', 'ITEM0000001'"""
    if pd.isna(val):
        return None
    val_str = str(val)
    match = re.search(r'\d+', val_str)
    return int(match.group(0)) if match else int(val)

def import_data():
    dataset_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "generated_dataset")
    
    cust_csv = os.path.join(dataset_dir, "customers.csv")
    prod_csv = os.path.join(dataset_dir, "products.csv")
    pur_csv = os.path.join(dataset_dir, "purchases.csv")
    items_csv = os.path.join(dataset_dir, "purchase_items.csv")
    
    for path in [cust_csv, prod_csv, pur_csv, items_csv]:
        if not os.path.exists(path):
            print(f"Error: Missing CSV file {path}. Run scripts/generate_dataset.py first.")
            return

    db_engine = getattr(Config, 'DB_TYPE', 'sqlite')
    print(f"Connecting to database ({db_engine.upper()})...")
    conn = get_db_connection(with_database=True)
    cursor = conn.cursor()
    
    if db_engine != 'sqlite':
        try:
            cursor.execute("ALTER TABLE customers ADD COLUMN city VARCHAR(50) DEFAULT NULL AFTER gender;")
        except Exception:
            pass
        try:
            cursor.execute("ALTER TABLE customers ADD COLUMN status VARCHAR(20) DEFAULT 'Active' AFTER city;")
        except Exception:
            pass
        try:
            cursor.execute("ALTER TABLE products ADD COLUMN status VARCHAR(20) DEFAULT 'Active' AFTER stock_quantity;")
        except Exception:
            pass

    print("Clearing existing table data...")
    if db_engine == 'sqlite':
        try:
            cursor.execute("PRAGMA foreign_keys = OFF;")
        except Exception:
            pass
        cursor.execute("DELETE FROM purchase_items;")
        cursor.execute("DELETE FROM purchases;")
        cursor.execute("DELETE FROM products;")
        cursor.execute("DELETE FROM customers;")
        try:
            cursor.execute("PRAGMA foreign_keys = ON;")
        except Exception:
            pass
    else:
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
        cursor.execute("TRUNCATE TABLE purchase_items;")
        cursor.execute("TRUNCATE TABLE purchases;")
        cursor.execute("TRUNCATE TABLE products;")
        cursor.execute("TRUNCATE TABLE customers;")
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")
    conn.commit()

    # 2. Import Products
    df_prod = pd.read_csv(prod_csv)
    print(f"Importing {len(df_prod)} products...")
    prod_tuples = []
    for _, row in df_prod.iterrows():
        prod_tuples.append((
            parse_id(row["product_id"]),
            row["product_name"],
            row["category"],
            float(row["price"]),
            int(row["stock_quantity"]),
            row.get("status", "Active"),
            row.get("description", "")
        ))
    cursor.executemany("""
        INSERT INTO products (product_id, name, category, price, stock_quantity, status, description)
        VALUES (%s, %s, %s, %s, %s, %s, %s);
    """, prod_tuples)
    conn.commit()

    # 3. Import Customers
    df_cust = pd.read_csv(cust_csv)
    print(f"Importing {len(df_cust)} customers...")
    cust_tuples = []
    for _, row in df_cust.iterrows():
        raw_phone = str(row["phone"]).strip().lstrip('+')
        if len(raw_phone) == 12 and raw_phone.startswith('91'):
            phone = raw_phone[2:]
        else:
            phone = raw_phone
        income_val = round(float(row["annual_income"])) if pd.notna(row["annual_income"]) else None
        cust_tuples.append((
            parse_id(row["customer_id"]),
            row["name"],
            row["email"],
            phone,
            income_val,
            int(row["age"]),
            row["gender"],
            row["city"],
            row.get("status", "Active"),
            str(row["created_at"])
        ))
    cursor.executemany("""
        INSERT INTO customers (customer_id, name, email, phone, income, age, gender, city, status, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
    """, cust_tuples)
    conn.commit()

    # 4. Import Purchases
    df_pur = pd.read_csv(pur_csv)
    print(f"Importing {len(df_pur)} purchases...")
    pur_tuples = []
    for _, row in df_pur.iterrows():
        pur_tuples.append((
            parse_id(row["purchase_id"]),
            parse_id(row["customer_id"]),
            float(row["total_amount"]),
            row["status"],
            str(row["purchase_date"])
        ))
    
    batch_size = 1000
    for i in range(0, len(pur_tuples), batch_size):
        cursor.executemany("""
            INSERT INTO purchases (purchase_id, customer_id, total_amount, status, purchase_date)
            VALUES (%s, %s, %s, %s, %s);
        """, pur_tuples[i:i+batch_size])
        conn.commit()

    # 5. Import Purchase Items
    df_items = pd.read_csv(items_csv)
    print(f"Importing {len(df_items)} purchase items...")
    item_tuples = []
    for _, row in df_items.iterrows():
        item_tuples.append((
            parse_id(row["purchase_item_id"]),
            parse_id(row["purchase_id"]),
            parse_id(row["product_id"]),
            int(row["quantity"]),
            float(row["unit_price"]),
            float(row["subtotal"])
        ))
    
    for i in range(0, len(item_tuples), batch_size):
        cursor.executemany("""
            INSERT INTO purchase_items (item_id, purchase_id, product_id, quantity, unit_price, subtotal)
            VALUES (%s, %s, %s, %s, %s, %s);
        """, item_tuples[i:i+batch_size])
        conn.commit()

    # Default Admin user with Werkzeug password hash for 'admin123'
    from werkzeug.security import generate_password_hash
    default_admin_hash = generate_password_hash("admin123")
    cursor.execute("""
        INSERT OR IGNORE INTO admins (admin_id, username, password_hash, email)
        VALUES (1, 'admin', %s, 'admin@example.com');
    """, (default_admin_hash,))
    conn.commit()

    # 7. Verification Summary
    print("\n" + "="*50)
    print(f"     {db_engine.upper()} DATABASE IMPORT SUMMARY REPORT")
    print("="*50)
    
    counts = {}
    for table in ["products", "customers", "purchases", "purchase_items", "admins"]:
        cursor.execute(f"SELECT COUNT(*) as cnt FROM {table};")
        res = cursor.fetchone()
        counts[table] = res["cnt"]
        
    print(f"Products in DB       : {counts['products']:>6} (CSV: {len(df_prod)})")
    print(f"Customers in DB      : {counts['customers']:>6} (CSV: {len(df_cust)})")
    print(f"Purchases in DB      : {counts['purchases']:>6} (CSV: {len(df_pur)})")
    print(f"Purchase Items in DB : {counts['purchase_items']:>6} (CSV: {len(df_items)})")
    print(f"Admins in DB         : {counts['admins']:>6}")
    print("="*50)
    print(f"SUCCESS: All generated dataset files imported directly into {db_engine.upper()}!")
    print("="*50 + "\n")
    
    conn.close()

if __name__ == "__main__":
    import_data()
