import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from werkzeug.security import check_password_hash, generate_password_hash
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

    # 1. Summary Metrics
    cust_total = execute_query("SELECT COUNT(*) as count FROM customers", fetch_one=True)['count'] or 0
    cust_active = execute_query("SELECT COUNT(*) as count FROM customers WHERE status = 'Active' OR status IS NULL", fetch_one=True)['count'] or 0
    cust_inactive = execute_query("SELECT COUNT(*) as count FROM customers WHERE status = 'Inactive'", fetch_one=True)['count'] or 0
    
    prod_total = execute_query("SELECT COUNT(*) as count FROM products", fetch_one=True)['count'] or 0
    prod_outofstock = execute_query("SELECT COUNT(*) as count FROM products WHERE status = 'Out of Stock' OR stock_quantity <= 0", fetch_one=True)['count'] or 0
    
    order_count = execute_query("SELECT COUNT(*) as count FROM purchases", fetch_one=True)['count'] or 0
    total_sales = execute_query("SELECT SUM(total_amount) as total FROM purchases", fetch_one=True)['total'] or 0.0
    
    clusters_res = execute_query("SELECT COUNT(DISTINCT cluster_label) as count FROM clusters", fetch_one=True)
    cluster_count = clusters_res['count'] if clusters_res and clusters_res['count'] else 0

    # 2. Category Sales Breakdown
    category_sales = execute_query("""
        SELECT p.category, 
               SUM(pi.quantity) as total_units,
               SUM(pi.subtotal) as total_revenue
        FROM purchase_items pi
        JOIN products p ON pi.product_id = p.product_id
        GROUP BY p.category
        ORDER BY total_revenue DESC
    """, fetch_all=True) or []

    # 3. Recent Purchases
    recent_orders = execute_query("""
        SELECT p.purchase_id, c.name as customer_name, c.phone as customer_phone, p.total_amount, p.purchase_date, p.status
        FROM purchases p
        JOIN customers c ON p.customer_id = c.customer_id
        ORDER BY p.purchase_date DESC LIMIT 6
    """, fetch_all=True) or []

    # 4. Existing Cluster Summary (if generated)
    cluster_summary = execute_query("""
        SELECT cluster_label, cluster_name, 
               COUNT(customer_id) as num_customers, 
               AVG(annual_income) as avg_income, 
               AVG(total_spending) as avg_spending
        FROM clusters
        GROUP BY cluster_label, cluster_name
        ORDER BY cluster_label
    """, fetch_all=True) or []

    return render_template(
        'admin/dashboard.html',
        cust_total=cust_total,
        cust_active=cust_active,
        cust_inactive=cust_inactive,
        prod_total=prod_total,
        prod_outofstock=prod_outofstock,
        order_count=order_count,
        total_sales=total_sales,
        cluster_count=cluster_count,
        category_sales=category_sales,
        recent_orders=recent_orders,
        cluster_summary=cluster_summary
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

@admin_bp.route('/customers/toggle-status/<int:customer_id>', methods=['POST'])
def toggle_customer_status(customer_id):
    if 'admin_id' not in session:
        return redirect(url_for('admin.login'))

    cust = execute_query("SELECT status FROM customers WHERE customer_id = %s", (customer_id,), fetch_one=True)
    if cust:
        new_status = 'Inactive' if cust.get('status') == 'Active' else 'Active'
        execute_query("UPDATE customers SET status = %s WHERE customer_id = %s", (new_status, customer_id), commit=True)
        flash(f"Customer #{customer_id} status updated to {new_status}.", "info")
    return redirect(url_for('admin.customers'))

@admin_bp.route('/customers/delete/<int:customer_id>', methods=['POST'])
def delete_customer(customer_id):
    if 'admin_id' not in session:
        return redirect(url_for('admin.login'))

    execute_query("DELETE FROM customers WHERE customer_id = %s", (customer_id,), commit=True)
    flash(f"Customer #{customer_id} deleted successfully.", "success")
    return redirect(url_for('admin.customers'))

@admin_bp.route('/products', methods=['GET', 'POST'])
def products():
    if 'admin_id' not in session:
        return redirect(url_for('admin.login'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        category = request.form.get('category', '').strip()
        price = request.form.get('price', type=float)
        stock = request.form.get('stock', type=int)
        description = request.form.get('description', '').strip()

        if not name or price is None or stock is None:
            flash("Product Name, Price, and Stock are required.", "warning")
            return redirect(url_for('admin.products'))

        status = 'Out of Stock' if stock <= 0 else 'Active'

        execute_query("""
            INSERT INTO products (name, category, price, stock_quantity, status, description)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (name, category, price, stock, status, description), commit=True)

        flash("Product added successfully!", "success")
        return redirect(url_for('admin.products'))

    products_list = execute_query("SELECT * FROM products ORDER BY category, name", fetch_all=True) or []
    return render_template('admin/products.html', products=products_list)

@admin_bp.route('/products/edit/<int:product_id>', methods=['POST'])
def edit_product(product_id):
    if 'admin_id' not in session:
        return redirect(url_for('admin.login'))

    name = request.form.get('name', '').strip()
    category = request.form.get('category', '').strip()
    price = request.form.get('price', type=float)
    stock = request.form.get('stock', type=int)
    description = request.form.get('description', '').strip()

    status = 'Out of Stock' if stock <= 0 else 'Active'

    execute_query("""
        UPDATE products 
        SET name = %s, category = %s, price = %s, stock_quantity = %s, status = %s, description = %s
        WHERE product_id = %s
    """, (name, category, price, stock, status, description, product_id), commit=True)

    flash(f"Product #{product_id} updated successfully.", "success")
    return redirect(url_for('admin.products'))

@admin_bp.route('/products/delete/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    if 'admin_id' not in session:
        return redirect(url_for('admin.login'))

    execute_query("DELETE FROM products WHERE product_id = %s", (product_id,), commit=True)
    flash(f"Product #{product_id} deleted successfully.", "success")
    return redirect(url_for('admin.products'))

@admin_bp.route('/purchases')
def purchases():
    if 'admin_id' not in session:
        return redirect(url_for('admin.login'))

    purchases_list = execute_query("""
        SELECT p.purchase_id, c.name as customer_name, c.phone as customer_phone,
               p.total_amount, p.purchase_date, p.status,
               COUNT(pi.item_id) as total_items
        FROM purchases p
        JOIN customers c ON p.customer_id = c.customer_id
        LEFT JOIN purchase_items pi ON p.purchase_id = pi.purchase_id
        GROUP BY p.purchase_id
        ORDER BY p.purchase_date DESC
    """, fetch_all=True) or []

    return render_template('admin/purchases.html', purchases=purchases_list)
