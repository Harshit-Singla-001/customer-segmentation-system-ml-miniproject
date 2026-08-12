-- Database Creation
CREATE DATABASE IF NOT EXISTS customer_segmentation_db
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

USE customer_segmentation_db;

-- 1. Admins Table
CREATE TABLE IF NOT EXISTS admins (
    admin_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- 2. Customers Table
CREATE TABLE IF NOT EXISTS customers (
    customer_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    phone VARCHAR(20) NOT NULL UNIQUE,
    income DECIMAL(12, 2) DEFAULT NULL,
    age INT DEFAULT NULL,
    gender VARCHAR(10) DEFAULT NULL,
    city VARCHAR(50) DEFAULT NULL,
    status VARCHAR(20) DEFAULT 'Active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- 3. Products Table
CREATE TABLE IF NOT EXISTS products (
    product_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    category VARCHAR(50) NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    stock_quantity INT NOT NULL DEFAULT 0,
    status VARCHAR(20) DEFAULT 'Active',
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- 4. Purchases (Orders) Table
CREATE TABLE IF NOT EXISTS purchases (
    purchase_id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    total_amount DECIMAL(12, 2) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'Completed',
    purchase_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_purchases_customer FOREIGN KEY (customer_id) 
        REFERENCES customers(customer_id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- 5. Purchase Items Table
CREATE TABLE IF NOT EXISTS purchase_items (
    item_id INT AUTO_INCREMENT PRIMARY KEY,
    purchase_id INT NOT NULL,
    product_id INT NOT NULL,
    quantity INT NOT NULL,
    unit_price DECIMAL(10, 2) NOT NULL,
    subtotal DECIMAL(12, 2) NOT NULL,
    CONSTRAINT fk_items_purchase FOREIGN KEY (purchase_id) 
        REFERENCES purchases(purchase_id) ON DELETE CASCADE,
    CONSTRAINT fk_items_product FOREIGN KEY (product_id) 
        REFERENCES products(product_id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- 6. Dataset Imports Metadata Table
CREATE TABLE IF NOT EXISTS dataset_imports (
    import_id INT AUTO_INCREMENT PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    filepath VARCHAR(255) NOT NULL,
    row_count INT NOT NULL DEFAULT 0,
    imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- 7. K-Means Cluster Results Table
CREATE TABLE IF NOT EXISTS clusters (
    cluster_id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT DEFAULT NULL,
    import_id INT DEFAULT NULL,
    cluster_label INT NOT NULL,
    cluster_name VARCHAR(50) NOT NULL,
    annual_income DECIMAL(12, 2) DEFAULT NULL,
    spending_score INT DEFAULT NULL,
    total_spending DECIMAL(12, 2) DEFAULT NULL,
    purchase_frequency INT DEFAULT NULL,
    algorithm VARCHAR(50) NOT NULL DEFAULT 'K-Means',
    k_value INT NOT NULL DEFAULT 3,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_clusters_customer FOREIGN KEY (customer_id) 
        REFERENCES customers(customer_id) ON DELETE SET NULL,
    CONSTRAINT fk_clusters_import FOREIGN KEY (import_id) 
        REFERENCES dataset_imports(import_id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- Initial Seed Data: Default Admin (Username: admin, Password: pbkdf2 hashed 'admin123')
INSERT IGNORE INTO admins (admin_id, username, password_hash, email) VALUES
(1, 'admin', 'scrypt:32768:8:1$kX5cQ9zX$447ed5d95e0c52eb20857ef51a7bc8ff8efd927a488ce9d084d5dfce7ddf0fb2', 'admin@example.com');

-- Initial Seed Data: Sample Products Catalog
INSERT IGNORE INTO products (product_id, name, category, price, stock_quantity, description) VALUES
(1, 'Wireless Bluetooth Headphones', 'Electronics', 89.99, 50, 'High quality noise cancelling over-ear headphones.'),
(2, 'Smart Fitness Watch', 'Electronics', 129.50, 35, 'Waterproof activity tracking watch with heart rate monitor.'),
(3, 'Ergonomic Leather Office Chair', 'Furniture', 249.99, 15, 'Adjustable high-back lumbar support office chair.'),
(4, 'Stainless Steel Water Bottle (1L)', 'Lifestyle', 19.99, 100, 'Double-wall vacuum insulated water flask.'),
(5, 'Mechanical RGB Gaming Keyboard', 'Electronics', 79.95, 40, 'Tactile mechanical switch keyboard with customizable lighting.');
