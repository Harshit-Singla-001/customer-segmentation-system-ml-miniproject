import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from app.db.connection import execute_query

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if not username or not password:
            flash("Username and password are required.", "warning")
            return render_template('admin/login.html')

        admin = execute_query("SELECT * FROM admins WHERE username = %s", (username,), fetch_one=True)
        if admin and check_password_hash(admin['password_hash'], password):
            session['admin_id'] = admin['admin_id']
            session['admin_username'] = admin['username']
            flash("Welcome Admin!", "success")
            return redirect(url_for('admin.dashboard'))
        else:
            flash("Invalid credentials.", "danger")

    return render_template('admin/login.html')

@admin_bp.route('/logout')
def logout():
    session.pop('admin_id', None)
    session.pop('admin_username', None)
    flash("Logged out successfully.", "info")
    return redirect(url_for('admin.login'))

@admin_bp.route('/dashboard')
def dashboard():
    if 'admin_id' not in session:
        return redirect(url_for('admin.login'))

    # Overview metrics
    cust_count = execute_query("SELECT COUNT(*) as count FROM customers", fetch_one=True)['count']
    prod_count = execute_query("SELECT COUNT(*) as count FROM products", fetch_one=True)['count']
    order_count = execute_query("SELECT COUNT(*) as count FROM purchases", fetch_one=True)['count']
    total_sales = execute_query("SELECT SUM(total_amount) as total FROM purchases", fetch_one=True)['total'] or 0.0

    recent_orders = execute_query("""
        SELECT p.purchase_id, c.name as customer_name, p.total_amount, p.purchase_date, p.status
        FROM purchases p
        JOIN customers c ON p.customer_id = c.customer_id
        ORDER BY p.purchase_date DESC LIMIT 5
    """, fetch_all=True) or []

    return render_template(
        'admin/dashboard.html',
        cust_count=cust_count,
        prod_count=prod_count,
        order_count=order_count,
        total_sales=total_sales,
        recent_orders=recent_orders
    )

@admin_bp.route('/customers')
def customers():
    if 'admin_id' not in session:
        return redirect(url_for('admin.login'))

    customers_list = execute_query("""
        SELECT c.*, 
               COALESCE(COUNT(p.purchase_id), 0) as order_count,
               COALESCE(SUM(p.total_amount), 0) as total_spent
        FROM customers c
        LEFT JOIN purchases p ON c.customer_id = p.customer_id
        GROUP BY c.customer_id
        ORDER BY c.created_at DESC
    """, fetch_all=True) or []

    return render_template('admin/customers.html', customers=customers_list)

@admin_bp.route('/products', methods=['GET', 'POST'])
def products():
    if 'admin_id' not in session:
        return redirect(url_for('admin.login'))

    if request.method == 'POST':
        name = request.form.get('name')
        category = request.form.get('category')
        price = request.form.get('price')
        stock = request.form.get('stock')
        description = request.form.get('description')

        query = """
            INSERT INTO products (name, category, price, stock_quantity, description)
            VALUES (%s, %s, %s, %s, %s)
        """
        execute_query(query, (name, category, float(price), int(stock), description), commit=True)
        flash("Product added successfully!", "success")
        return redirect(url_for('admin.products'))

    products_list = execute_query("SELECT * FROM products ORDER BY category, name", fetch_all=True) or []
    return render_template('admin/products.html', products=products_list)
