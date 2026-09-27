-- SQLite Schema for Customer Segmentation System
-- Tables: admins, customers, products, purchases, purchase_items, dataset_imports, clusters

PRAGMA foreign_keys = ON;

-- 1. Admins Table
CREATE TABLE IF NOT EXISTS admins (
    admin_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Customers Table
CREATE TABLE IF NOT EXISTS customers (
    customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    phone TEXT NOT NULL UNIQUE,
    income REAL DEFAULT NULL,
    age INTEGER DEFAULT NULL,
    gender TEXT DEFAULT NULL,
    city TEXT DEFAULT NULL,
    status TEXT DEFAULT 'Active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Products Table
CREATE TABLE IF NOT EXISTS products (
    product_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    price REAL NOT NULL,
    stock_quantity INTEGER NOT NULL DEFAULT 0,
    status TEXT DEFAULT 'Active',
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Purchases (Orders) Table
CREATE TABLE IF NOT EXISTS purchases (
    purchase_id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    total_amount REAL NOT NULL,
    status TEXT NOT NULL DEFAULT 'Completed',
    purchase_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE
);

-- 5. Purchase Items Table
CREATE TABLE IF NOT EXISTS purchase_items (
    item_id INTEGER PRIMARY KEY AUTOINCREMENT,
    purchase_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price REAL NOT NULL,
    subtotal REAL NOT NULL,
    FOREIGN KEY (purchase_id) REFERENCES purchases(purchase_id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE CASCADE
);

-- 6. Dataset Imports Metadata Table
CREATE TABLE IF NOT EXISTS dataset_imports (
    import_id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    filepath TEXT NOT NULL,
    row_count INTEGER NOT NULL DEFAULT 0,
    imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 7. K-Means Cluster Results Table
CREATE TABLE IF NOT EXISTS clusters (
    cluster_id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER DEFAULT NULL,
    import_id INTEGER DEFAULT NULL,
    cluster_label INTEGER NOT NULL,
    cluster_name TEXT NOT NULL,
    annual_income REAL DEFAULT NULL,
    spending_score INTEGER DEFAULT NULL,
    total_spending REAL DEFAULT NULL,
    purchase_frequency INTEGER DEFAULT NULL,
    algorithm TEXT NOT NULL DEFAULT 'K-Means',
    k_value INTEGER NOT NULL DEFAULT 3,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE SET NULL,
    FOREIGN KEY (import_id) REFERENCES dataset_imports(import_id) ON DELETE CASCADE
);

-- Default Admin User (admin / admin123)
INSERT OR IGNORE INTO admins (admin_id, username, password_hash, email) VALUES
(1, 'admin', 'scrypt:32768:8:1$bfQrgE8u7beKZTsx$e0dfea1be5a895c9c7853dfb76cf13adcb5d5586ced0c9c0e1df38847608cde5d67e3b89507d82bb3a212c0709003e22331418fb58797b5045fdc8c2d0452858', 'admin@example.com');

-- Default Seed Products (if not loaded from CSV)
INSERT OR IGNORE INTO products (product_id, name, category, price, stock_quantity, description) VALUES
(1, 'Wireless Bluetooth Headphones', 'Electronics', 89.99, 50, 'High quality noise cancelling over-ear headphones.'),
(2, 'Smart Fitness Watch', 'Electronics', 129.50, 35, 'Waterproof activity tracking watch with heart rate monitor.'),
(3, 'Ergonomic Leather Office Chair', 'Furniture', 249.99, 15, 'Adjustable high-back lumbar support office chair.'),
(4, 'Stainless Steel Water Bottle (1L)', 'Lifestyle', 19.99, 100, 'Double-wall vacuum insulated water flask.'),
(5, 'Mechanical RGB Gaming Keyboard', 'Electronics', 79.95, 40, 'Tactile mechanical switch keyboard with customizable lighting.');
