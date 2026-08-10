# Customer Segmentation System using K-Means Clustering

An educational full-stack DBMS & Data Science project built with **Flask**, **MySQL**, and **K-Means Clustering (Scikit-Learn)**.

---

## 📌 Overview

The **Customer Segmentation System** demonstrates how customer details, purchasing history, and imported datasets are stored in a MySQL relational database and analyzed using machine learning (K-Means Clustering) to discover customer segments.

### Key Capabilities
- **Shopping Simulation**: Browse products, add items to cart, and place orders.
- **Admin Dashboard**: Manage products, customers, transactions, and imported datasets.
- **Data Preprocessing & Segmentation**: Standardize numerical customer metrics (spending, frequency, income, age) and apply K-Means clustering.
- **Interactive Visualizations & Analytics**: View cluster distributions, segment characteristics, and download reports.

---

## 🛠️ Tech Stack

- **Backend**: Python 3.x, Flask, MySQL Connector / SQLAlchemy
- **Database**: MySQL 8.x
- **Machine Learning & Data Processing**: Pandas, NumPy, Scikit-Learn
- **Frontend**: HTML5, CSS3 (Vanilla), JavaScript (ES6+), Chart.js

---

## 📁 Project Structure

```
customer-segmentation-system/
├── app/                     # Flask Application Source Code
│   ├── static/              # CSS, JS, and Images
│   ├── templates/           # HTML Jinja2 Templates
│   ├── routes/              # Blueprint Route Handlers
│   ├── services/            # Business Logic & Service Layer
│   ├── db/                  # Database Connections & Queries
│   └── ml/                  # K-Means Machine Learning Pipeline
├── sql/                     # Database Schemas and Seed Data
├── uploads/                 # Storage for imported CSV datasets
├── config.py                # Environment Configuration
├── app.py                   # Application Entry Point
├── requirements.txt         # Python Dependencies
├── .env.example             # Environment Variables Template
└── README.md                # Project Documentation
```

---

## 🚀 Getting Started

### Prerequisites
- Python 3.9+
- MySQL Server 8.0+

### Setup Instructions

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-username/customer-segmentation-system.git
   cd customer-segmentation-system
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Database Configuration**
   - Copy `.env.example` to `.env` and set your MySQL credentials.
   - Import the database schema from `sql/schema.sql`.

5. **Run the Application**
   ```bash
   python app.py
   ```
   Open `http://127.0.0.1:5000` in your browser.

---

## 📄 License
Educational / Open Source Project.
