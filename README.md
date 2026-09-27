# Customer Segmentation System using K-Means Clustering

An educational full-stack Data Science & Machine Learning web application built with **Flask**, **SQLite / MySQL**, and **K-Means Clustering (Scikit-Learn)**.

---

## 📌 Overview

The **Customer Segmentation System** demonstrates how customer profiles, purchasing history, and transactional metrics are stored in a relational database and analyzed using unsupervised machine learning (**K-Means Clustering**) to segment customers into actionable behavioural groups.

### Key Capabilities
- **Fast Self-Seeding Database**: Powered by zero-configuration SQLite (`instance/customer_segmentation.db`) with smart conditional startup checks that load seeded demo data instantly without repetitive slow imports (with optional MySQL cloud support).
- **Instant 3-Cluster Segmentation**: Customers are partitioned into exactly **3 distinct behavioral clusters**:
  - 🌟 **High Paying Customer** (High income, high spending, premium buyers)
  - 🔷 **Average Customer** (Moderate income and steady spending frequency)
  - 🏷️ **Budget Customer** (Value-conscious customers with lower spending)
- **Real-Time Dynamic Clustering**:
  - **New Customers**: Instantly classified into one of the 3 clusters upon their first checkout/registration.
  - **Returning Customers**: Automatically re-evaluated and reassigned whenever new purchases alter their spending, frequency, or recency profile.
- **Demographic Sub-Segment Analysis**: Leverages customer `age` into demographic brackets (Youth 18–29, Middle-Aged 30–49, Senior 50+) mapped across the 3 clusters.
- **Clean Customer Directory**: View customers with whole-number annual income (no decimals), clean 10-digit phone numbers, and full-row multi-factor filtering & sorting (Customer ID, Name, Age, Income, Total Spent, Orders, Recency, Segment). Actions column is cleanly removed.
- **Advanced Product Catalog Management**: Full-row multi-factor filtering & sorting (Product ID, Name, Category, Price, Stock Quantity, Stock Status) including a dedicated **Out of Stock** filter.
- **Interactive Executive Dashboard**: 5 linked high-level KPI cards, interactive 2D Chart.js scatter plot (Annual Income vs Total Spending), highlighted Re-run K-Means trigger, and clickable segment cards linking directly to filtered customer lists.
- **Dynamic Device Timezone Engine**: Automatically calculates Indian Standard Time (IST — Asia/Kolkata / UTC+5:30) timestamps for transaction records.

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

- **Backend**: Python 3.9+, Flask, Scikit-Learn, Pandas, NumPy, Joblib
- **Database**: SQLite (default `instance/customer_segmentation.db`) / MySQL 8.x compatible
- **Machine Learning**: K-Means Clustering (`n_clusters=3`), StandardScaler, Real-Time Online Inference
- **Frontend**: HTML5, Vanilla CSS3 (Custom Design System with Light/Dark Mode), JavaScript (ES6+), Chart.js
- **Timezone Engine**: Dynamic device system clock calculation with IST (`Asia/Kolkata`) conversion

---

## 📁 Project Structure

```
customer-segmentation-system/
├── app/                     # Flask Application Source Code
│   ├── static/              # CSS, JS, and UI static assets
│   ├── templates/           # Jinja2 HTML Templates
│   │   ├── admin/           # Admin Dashboard, Customers, Products, Purchases, Imports
│   │   ├── customer/        # Storefront, Cart, Checkout
│   │   └── base.html        # Main Layout & Global Theme Toggle
│   ├── routes/              # Blueprint Handlers (main, customer, admin)
│   ├── services/            # Business Logic & Analytical Services
│   ├── db/                  # SQLite & MySQL Connection & Compatibility Handlers
│   └── ml/                  # K-Means Machine Learning Pipeline & Serialized Models
├── generated_dataset/       # Initial Seed Datasets
│   ├── customers.csv        # Customer Demographic Records
│   ├── products.csv         # Product Catalog Items
│   ├── purchases.csv        # Order Master Records
│   └── purchase_items.csv   # Order Line Items
├── instance/                # SQLite Database Storage
│   └── customer_segmentation.db
├── scripts/                 # Utility Scripts
│   ├── generate_dataset.py  # Synthetic Dataset Generator Engine
│   ├── import_to_db.py      # Bulk Importer Script
│   └── init_db.py          # Database Initializer
├── sql/                     # Relational Schemas
│   └── schema.sql           # Table Definitions & Indexes
├── config.py                # App Configuration & Environment Loader
├── app.py                   # Flask Application Entrypoint
├── requirements.txt         # Project Dependencies
├── .env                     # Environment Configuration
└── README.md                # Project Documentation
```

---

## 🚀 Quickstart Guide

### 1. Prerequisites
- Python 3.9+ installed

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the Application
```bash
python app.py
```
*Note: On initial startup, the application automatically verifies if SQLite tables and seed data exist. If not, it self-seeds the database and fits the initial K-Means model in seconds.*

Open **[http://127.0.0.1:5000](http://127.0.0.1:5000)** in your browser.

---

## 📊 Dashboard & Features Highlights

### 1. Five Core Metric Cards
The admin dashboard highlights 5 essential metrics with direct navigational deep-links:
1. **Registered Customers** ➔ Links directly to `/admin/customers`
2. **Products in Catalog** ➔ Links directly to `/admin/products`
3. **Out-of-Stock Products** ➔ Links directly to `/admin/products?stock_status=out_of_stock`
4. **Total Orders Placed** ➔ Links directly to `/admin/purchases`
5. **Customer Segments** ➔ Smooth scrolls directly to the Customer Segmentation overview

### 2. Customer Segmentation (3 Clusters)
- **High Paying Customer**: High annual income and high lifetime spending.
- **Average Customer**: Moderate income with dependable order frequency.
- **Budget Customer**: Value-oriented customers with lower purchase amounts.
- Each cluster card displays customer count, percentage share, average spending, average income, and Age demographic breakdown (Youth, Middle-Aged, Senior).
- Clicking any cluster card instantly filters the customer list by that segment (`/admin/customers?segment=...`).

### 3. Customer & Product Multi-Factor Filtering
- **Customer List**: Independent dropdown filters for Customer ID, Customer Name, Age, Annual Income, Total Spent, Total Orders, Recency, and Segment. Default order is High → Low.
- **Product List**: Independent dropdown filters for Product ID, Product Name, Category, Price, Stock Quantity, and Stock Status (`All`, `In Stock`, `Out of Stock`).

---

## 📄 License
Educational / Open Source Machine Learning & Data Science Project.
