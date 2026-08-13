# Customer Segmentation System using K-Means Clustering

An educational full-stack DBMS & Data Science project built with **Flask**, **MySQL**, and **K-Means Clustering (Scikit-Learn)**.

---

## 📌 Overview

The **Customer Segmentation System** demonstrates how customer details, purchasing history, and imported datasets are stored in a MySQL relational database and analyzed using machine learning (K-Means Clustering) to discover customer segments.

### Key Capabilities
- **Synthetic Dataset Generator**: Create realistic, seedable, normalized datasets with hidden customer behavior profiles (`scripts/generate_dataset.py`).
- **Direct Database Importer**: High-performance bulk import of CSV records into online MySQL (`scripts/import_to_db.py`).
- **Phone-First Customer Verification**: Instant 10-digit mobile lookup (`/customer/check-customer?phone=...`) for 1-click checkout or dynamic new customer registration.
- **Demographic Segmentation**: Captures `age` and `gender` alongside `income` and purchase metrics for multi-dimensional K-Means clustering.
- **Dynamic Device Timezone Engine**: Dynamically inspects the host device system clock and converts transaction timestamps to Indian Standard Time (IST — Asia/Kolkata / UTC+5:30).
- **Admin Management Panel**: Single-screen optimized dashboards for managing catalog items, customers (with direct Delete actions), transactions, imports, and analytical segment visualization.
- **K-Means Analytics**: Standardize numerical customer metrics (spending, frequency, income, age) and analyze discovered customer segments.

---

## 🔑 Default Admin Credentials

To access the Administrator Dashboard, navigate to `http://127.0.0.1:5000/admin/login` and use the following seeded admin credentials:

| Setting | Value |
| :--- | :--- |
| **Admin Login URL** | `http://127.0.0.1:5000/admin/login` |
| **Username** | `admin` |
| **Password** | `admin123` |
| **Email** | `admin@example.com` |

---

## 🛠️ Tech Stack

- **Backend**: Python 3.x, Flask, PyMySQL (with SSL support)
- **Database**: MySQL 8.x (Cloud MySQL on Aiven / Local MySQL)
- **Machine Learning & Analytics**: Pandas, NumPy, Scikit-Learn, Faker
- **Frontend**: HTML5, Vanilla CSS3, JavaScript (ES6+), Chart.js
- **Timezone Engine**: Dynamic device system clock inspection with IST (`Asia/Kolkata`) calculation

---

## 📁 Project Structure

```
customer-segmentation-system/
├── app/                     # Flask Application Source Code
│   ├── static/              # CSS, JS, and UI static assets
│   ├── templates/           # Jinja2 HTML Templates
│   ├── routes/              # Blueprint Handlers (main, customer, admin)
│   ├── services/            # Business Logic & Analytical Services
│   ├── db/                  # PyMySQL Connection & Query Handlers
│   └── ml/                  # K-Means Machine Learning Pipeline
├── generated_dataset/       # Output CSVs from Synthetic Dataset Generator
│   ├── customers.csv        # 750 Customer Records
│   ├── products.csv         # 20 Product Catalog Items
│   ├── purchases.csv        # 7,500 Order Master Records
│   ├── purchase_items.csv   # 13,057 Order Line Items
│   ├── customer_features.csv# 750 Derived Customer Analytical Metrics
│   └── dataset_summary.txt  # Dataset Analytical Summary Report
├── scripts/                 # Utility & Dataset Generator Scripts
│   ├── generate_dataset.py  # Synthetic Dataset Generator Engine
│   ├── import_to_db.py      # MySQL Bulk Importer Script
│   └── init_db.py          # Database Schema Initializer
├── sql/                     # Relational Schemas and Initial Seeds
│   └── schema.sql           # MySQL Table Definitions & Indexes
├── uploads/                 # Storage for imported CSV datasets
├── config.py                # App Configuration & Environment Loader
├── app.py                   # Flask Application Entrypoint
├── requirements.txt         # Project Dependencies
├── .env                     # Database & Environment Secrets
└── README.md                # Project Documentation
```

---

## 🚀 Quickstart Guide

### 1. Prerequisites
- Python 3.9+ installed
- MySQL Server 8.0+ (or active Aiven Cloud MySQL connection)

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Initialize Database & Import Data

1. **Configure Environment Variables**: Ensure your `.env` contains valid MySQL credentials:
   ```env
   DB_HOST=mysql-10da54c1-customer-segmentation.j.aivencloud.com
   DB_PORT=21978
   DB_USER=avnadmin
   DB_PASSWORD=YOUR_PASSWORD
   DB_NAME=customer_segmentation_db
   DB_SSL=true
   ```

2. **Initialize Database Tables**:
   ```bash
   python scripts/init_db.py
   ```

3. **Generate Synthetic Dataset (Optional)**:
   ```bash
   python scripts/generate_dataset.py
   ```

4. **Bulk Import Data into MySQL**:
   ```bash
   python scripts/import_to_db.py
   ```

### 4. Run the Application
```bash
python app.py
```
Open **[http://127.0.0.1:5000](http://127.0.0.1:5000)** in your browser.

---

## 📊 Database Entities & Schema

- **`customers`**: Customer demographics (`customer_id`, `name`, `email`, `phone`, `income`, `age`, `gender`, `city`, `created_at`)
- **`products`**: Item catalog (`product_id`, `name`, `category`, `price`, `stock_quantity`, `status`, `description`)
- **`purchases`**: Transaction records (`purchase_id`, `customer_id`, `total_amount`, `status`, `purchase_date`)
- **`purchase_items`**: Itemized order lines (`item_id`, `purchase_id`, `product_id`, `quantity`, `unit_price`, `subtotal`)
- **`admins`**: Secured administrator accounts (`admin_id`, `username`, `password_hash`, `email`)
- **`clusters`**: K-Means segmentation results (`cluster_id`, `customer_id`, `cluster_label`, `cluster_name`, `annual_income`, `total_spending`, `purchase_frequency`, `algorithm`)

---

## 📄 License
Educational / Open Source DBMS & ML Project.
