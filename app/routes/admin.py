from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from app.db.connection import execute_query, get_db_connection

admin_bp = Blueprint('admin', __name__)

CUSTOMER_SORT_COLUMNS = {
    'customer_id': 'c.customer_id',
    'name':        'c.name',
    'phone':       'c.phone',
    'income':      'c.income',
    'age':         'c.age',
    'order_count': 'order_count',
    'total_spent': 'total_spent',
    'segment':     'cl.cluster_label',
    'status':      'c.status'
}

# ── Auth Routes ──────────────────────────────────────────────────────────

@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'admin_id' in session:
        return redirect(url_for('admin.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if not username or not password:
            flash("Username and password are required.", "warning")
            return render_template('admin/login.html')

        admin = execute_query(
            "SELECT * FROM admins WHERE username = %s",
            (username,), fetch_one=True
        )

        from werkzeug.security import check_password_hash
        if admin and check_password_hash(admin['password_hash'], password):
            session['admin_id'] = admin['admin_id']
            session['admin_user'] = admin['username']
            session['admin_username'] = admin['username']
            flash(f"Welcome back, {admin['username']}!", "success")
            return redirect(url_for('admin.dashboard'))
        else:
            flash("Invalid username or password.", "danger")

    return render_template('admin/login.html')


@admin_bp.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for('main.index'))


# ── Dashboard ────────────────────────────────────────────────────────────

@admin_bp.route('/dashboard')
def dashboard():
    if 'admin_id' not in session:
        return redirect(url_for('admin.login'))

    # Combine all summary metrics into ONE single query on 1 DB connection
    metrics = execute_query("""
        SELECT 
            (SELECT COUNT(*) FROM customers) as cust_total,
            (SELECT COUNT(*) FROM customers WHERE status = 'Active' OR status IS NULL) as cust_active,
            (SELECT COUNT(*) FROM customers WHERE status = 'Inactive') as cust_inactive,
            (SELECT COUNT(*) FROM products) as prod_total,
            (SELECT COUNT(*) FROM products WHERE status = 'Out of Stock' OR stock_quantity <= 0) as prod_outofstock,
            (SELECT COUNT(*) FROM purchases) as order_count,
            (SELECT COALESCE(SUM(total_amount), 0) FROM purchases) as total_sales,
            (SELECT COUNT(DISTINCT cluster_label) FROM clusters) as cluster_count
    """, fetch_one=True) or {}

    cust_total      = metrics.get('cust_total', 0)
    cust_active     = metrics.get('cust_active', 0)
    cust_inactive   = metrics.get('cust_inactive', 0)
    prod_total      = metrics.get('prod_total', 0)
    prod_outofstock = metrics.get('prod_outofstock', 0)
    order_count     = metrics.get('order_count', 0)
    total_sales     = float(metrics.get('total_sales', 0.0) or 0.0)
    cluster_count   = metrics.get('cluster_count', 0)

    import json
    from app.ml.clustering import get_dashboard_ml_data
    ml_data = get_dashboard_ml_data()
    cluster_summary = ml_data['cluster_summary']
    scatter_data_json = json.dumps(ml_data['scatter_data'])
    elbow_data_json = json.dumps(ml_data['elbow_data'])
    strategies = ml_data['strategies']

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
        cluster_summary=cluster_summary,
        scatter_data_json=scatter_data_json,
        elbow_data_json=elbow_data_json,
        strategies=strategies
    )


@admin_bp.route('/recluster', methods=['POST', 'GET'])
def recluster():
    if 'admin_id' not in session:
        return redirect(url_for('admin.login'))
    from app.ml.clustering import train_kmeans_model
    success, summary = train_kmeans_model(save=True)
    if success:
        flash(f"K-Means clustering completed! {summary.get('total_customers', 0)} customers segmented into 3 clusters.", "success")
    else:
        flash(f"Error training clustering model: {summary}", "danger")
    return redirect(url_for('admin.dashboard'))


# ── Customer Management (with sorting & pagination) ──────────────────────

@admin_bp.route('/customers')
def customers():
    if 'admin_id' not in session:
        return redirect(url_for('admin.login'))

    sort_by  = request.args.get('sort_by', 'total_spent')
    sort_dir = request.args.get('sort_dir', 'desc')
    page     = request.args.get('page', 1, type=int)
    segment  = request.args.get('segment', '').strip()

    if page < 1:
        page = 1
    per_page = 30

    if sort_by not in CUSTOMER_SORT_COLUMNS:
        sort_by = 'total_spent'
    if sort_dir not in ('asc', 'desc'):
        sort_dir = 'desc'

    sql_col = CUSTOMER_SORT_COLUMNS[sort_by]
    sql_dir = 'ASC' if sort_dir == 'asc' else 'DESC'

    where_clauses = []
    where_params = []
    if segment:
        where_clauses.append("cl.cluster_name = %s")
        where_params.append(segment)

    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    conn = None
    try:
        conn = get_db_connection(with_database=True)
        with conn.cursor() as cursor:
            # 1. Total count
            count_query = f"""
                SELECT COUNT(DISTINCT c.customer_id) as count 
                FROM customers c
                LEFT JOIN clusters cl ON c.customer_id = cl.customer_id
                {where_sql}
            """
            if where_params:
                cursor.execute(count_query, tuple(where_params))
            else:
                cursor.execute(count_query)
            total_res = cursor.fetchone()
            total_customers = total_res['count'] if total_res and total_res['count'] else 0
            total_pages = max(1, (total_customers + per_page - 1) // per_page)
            if page > total_pages:
                page = total_pages

            offset = (page - 1) * per_page

            # 2. Paginated customers data
            data_query = f"""
                SELECT c.*,
                       COALESCE(COUNT(DISTINCT p.purchase_id), 0) as order_count,
                       COALESCE(SUM(p.total_amount), 0)           as total_spent,
                       cl.cluster_label,
                       cl.cluster_name
                FROM customers c
                LEFT JOIN purchases p  ON c.customer_id = p.customer_id
                LEFT JOIN clusters  cl ON c.customer_id = cl.customer_id
                {where_sql}
                GROUP BY c.customer_id, cl.cluster_label, cl.cluster_name
                ORDER BY {sql_col} {sql_dir}
                LIMIT %s OFFSET %s
            """
            cursor.execute(data_query, tuple(where_params + [per_page, offset]))
            customers_list = cursor.fetchall() or []
    except Exception as e:
        customers_list = []
        total_customers = 0
        total_pages = 1
    finally:
        if conn:
            conn.close()

    return render_template(
        'admin/customers.html',
        customers=customers_list,
        sort_by=sort_by,
        sort_dir=sort_dir,
        segment=segment,
        page=page,
        total_pages=total_pages,
        total_customers=total_customers,
        per_page=per_page
    )


@admin_bp.route('/customers/toggle-status/<int:customer_id>', methods=['POST'])
def toggle_customer_status(customer_id):
    if 'admin_id' not in session:
        return redirect(url_for('admin.login'))

    page = request.args.get('page', 1, type=int)
    sort_by = request.args.get('sort_by', 'total_spent')
    sort_dir = request.args.get('sort_dir', 'desc')
    segment = request.args.get('segment', '').strip()

    cust = execute_query("SELECT status FROM customers WHERE customer_id = %s", (customer_id,), fetch_one=True)
    if cust:
        new_status = 'Inactive' if cust.get('status') == 'Active' else 'Active'
        execute_query("UPDATE customers SET status = %s WHERE customer_id = %s", (new_status, customer_id), commit=True)
        flash(f"Customer #{customer_id} status updated to {new_status}.", "info")
    return redirect(url_for('admin.customers', page=page, sort_by=sort_by, sort_dir=sort_dir, segment=segment))


@admin_bp.route('/customers/delete/<int:customer_id>', methods=['POST'])
def delete_customer(customer_id):
    if 'admin_id' not in session:
        return redirect(url_for('admin.login'))

    page = request.args.get('page', 1, type=int)
    sort_by = request.args.get('sort_by', 'customer_id')
    sort_dir = request.args.get('sort_dir', 'asc')

    execute_query("DELETE FROM customers WHERE customer_id = %s", (customer_id,), commit=True)
    flash(f"Customer #{customer_id} deleted successfully.", "success")
    return redirect(url_for('admin.customers', page=page, sort_by=sort_by, sort_dir=sort_dir))


# ── Product Management ───────────────────────────────────────────────────

@admin_bp.route('/products', methods=['GET', 'POST'])
def products():
    if 'admin_id' not in session:
        return redirect(url_for('admin.login'))

    if request.method == 'POST':
        name        = request.form.get('name', '').strip()
        category    = request.form.get('category', '').strip()
        price       = request.form.get('price', type=float)
        stock       = request.form.get('stock', type=int)
        description = request.form.get('description', '').strip()

        if not name:
            flash("Product name is required.", "warning")
            return redirect(url_for('admin.products'))
        if price is None or price < 0:
            flash("Price must be a valid non-negative number.", "warning")
            return redirect(url_for('admin.products'))
        if stock is None or stock < 0:
            flash("Stock quantity must be a valid non-negative number.", "warning")
            return redirect(url_for('admin.products'))

        status = 'Out of Stock' if stock <= 0 else 'Active'

        execute_query("""
            INSERT INTO products (name, category, price, stock_quantity, status, description)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (name, category, price, stock, status, description), commit=True)

        flash(f"Product '{name}' added successfully!", "success")
        return redirect(url_for('admin.products'))

    sort_by      = request.args.get('sort_by', 'product_id').strip()
    sort_dir     = request.args.get('sort_dir', 'desc').strip()
    stock_status = request.args.get('stock_status', '').strip().lower()
    category     = request.args.get('category', '').strip()

    PRODUCT_SORT_COLUMNS = {
        'product_id':     'product_id',
        'id':             'product_id',
        'name':           'name',
        'category':       'category',
        'price':          'price',
        'stock_quantity': 'stock_quantity',
        'stock':          'stock_quantity',
        'status':         'status'
    }
    if sort_by not in PRODUCT_SORT_COLUMNS:
        sort_by = 'product_id'
    if sort_dir not in ('asc', 'desc'):
        sort_dir = 'desc'

    sql_col = PRODUCT_SORT_COLUMNS[sort_by]
    sql_dir = 'ASC' if sort_dir == 'asc' else 'DESC'

    where_clauses = []
    params = []

    if stock_status == 'out_of_stock':
        where_clauses.append("(status = 'Out of Stock' OR stock_quantity <= 0)")
    elif stock_status == 'in_stock':
        where_clauses.append("(status = 'Active' AND stock_quantity > 0)")

    if category:
        where_clauses.append("category = %s")
        params.append(category)

    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    query = f"SELECT * FROM products {where_sql} ORDER BY {sql_col} {sql_dir}"
    products_list = execute_query(query, tuple(params) if params else None, fetch_all=True) or []

    cat_rows = execute_query("SELECT DISTINCT category FROM products WHERE category IS NOT NULL AND category != '' ORDER BY category", fetch_all=True) or []
    categories = [r['category'] for r in cat_rows]

    return render_template(
        'admin/products.html',
        products=products_list,
        sort_by=sort_by,
        sort_dir=sort_dir,
        stock_status=stock_status,
        category=category,
        categories=categories
    )


@admin_bp.route('/products/get/<int:product_id>')
def get_product(product_id):
    """JSON endpoint — returns current product data for the edit modal."""
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    product = execute_query(
        "SELECT * FROM products WHERE product_id = %s",
        (product_id,), fetch_one=True
    )
    if not product:
        return jsonify({'error': 'Product not found'}), 404

    return jsonify({
        'product_id':   product['product_id'],
        'name':         product['name'],
        'category':     product['category'] or '',
        'price':        float(product['price']),
        'stock':        product['stock_quantity'],
        'description':  product['description'] or '',
        'status':       product['status'],
    })


@admin_bp.route('/products/edit/<int:product_id>', methods=['POST'])
def edit_product(product_id):
    if 'admin_id' not in session:
        return redirect(url_for('admin.login'))

    name        = request.form.get('name', '').strip()
    category    = request.form.get('category', '').strip()
    price       = request.form.get('price', type=float)
    stock       = request.form.get('stock', type=int)
    description = request.form.get('description', '').strip()

    if not name:
        flash("Product name cannot be empty.", "warning")
        return redirect(url_for('admin.products'))
    if price is None or price < 0:
        flash("Price must be a valid non-negative number.", "warning")
        return redirect(url_for('admin.products'))
    if stock is None or stock < 0:
        flash("Stock quantity must be a valid non-negative number.", "warning")
        return redirect(url_for('admin.products'))

    status = 'Out of Stock' if stock <= 0 else 'Active'

    execute_query("""
        UPDATE products
        SET name = %s, category = %s, price = %s, stock_quantity = %s, status = %s, description = %s
        WHERE product_id = %s
    """, (name, category, price, stock, status, description, product_id), commit=True)

    flash(f"Product '{name}' updated successfully.", "success")
    return redirect(url_for('admin.products'))


@admin_bp.route('/products/delete/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    if 'admin_id' not in session:
        return redirect(url_for('admin.login'))

    execute_query("DELETE FROM products WHERE product_id = %s", (product_id,), commit=True)
    flash(f"Product #{product_id} deleted successfully.", "success")
    return redirect(url_for('admin.products'))


# ── Purchase Management (with search & pagination) ───────────────────────

@admin_bp.route('/purchases')
def purchases():
    if 'admin_id' not in session:
        return redirect(url_for('admin.login'))

    page = request.args.get('page', 1, type=int)
    if page < 1:
        page = 1
    per_page = 30

    q_id    = request.args.get('q_id', '').strip()
    q_name  = request.args.get('q_name', '').strip()
    q_phone = request.args.get('q_phone', '').strip()
    q_date  = request.args.get('q_date', '').strip()
    sort_by = request.args.get('sort_by', 'newest').strip()

    if sort_by == 'oldest':
        sql_order = "p.purchase_id ASC"
    elif sort_by == 'highest':
        sql_order = "p.total_amount DESC, p.purchase_id DESC"
    elif sort_by == 'lowest':
        sql_order = "p.total_amount ASC, p.purchase_id ASC"
    else:
        sort_by = 'newest'
        sql_order = "p.purchase_id DESC"

    where_clauses = []
    params = []

    if q_id:
        if q_id.isdigit():
            where_clauses.append("p.purchase_id = %s")
            params.append(int(q_id))
        else:
            where_clauses.append("p.purchase_id = -1")

    if q_name:
        where_clauses.append("c.name LIKE %s")
        params.append(f"%{q_name}%")

    if q_phone:
        where_clauses.append("c.phone LIKE %s")
        params.append(f"%{q_phone}%")

    if q_date:
        where_clauses.append("DATE(p.purchase_date) = %s")
        params.append(q_date)

    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    conn = None
    try:
        conn = get_db_connection(with_database=True)
        with conn.cursor() as cursor:
            # 1. Total count
            count_query = f"""
                SELECT COUNT(DISTINCT p.purchase_id) as count
                FROM purchases p
                JOIN customers c ON p.customer_id = c.customer_id
                {where_sql}
            """
            cursor.execute(count_query, tuple(params))
            count_res = cursor.fetchone()
            total_purchases = count_res['count'] if count_res and count_res['count'] else 0

            total_pages = max(1, (total_purchases + per_page - 1) // per_page)
            if page > total_pages:
                page = total_pages

            offset = (page - 1) * per_page

            # 2. Paginated transactions data
            data_query = f"""
                SELECT p.purchase_id, c.name as customer_name, c.phone as customer_phone,
                       p.total_amount, p.purchase_date, p.status,
                       COUNT(pi.item_id) as total_items
                FROM purchases p
                JOIN customers c ON p.customer_id = c.customer_id
                LEFT JOIN purchase_items pi ON p.purchase_id = pi.purchase_id
                {where_sql}
                GROUP BY p.purchase_id, c.name, c.phone, p.total_amount, p.purchase_date, p.status
                ORDER BY {sql_order}
                LIMIT %s OFFSET %s
            """
            data_params = tuple(params + [per_page, offset])
            cursor.execute(data_query, data_params)
            purchases_list = cursor.fetchall() or []
    except Exception as e:
        purchases_list = []
        total_purchases = 0
        total_pages = 1
    finally:
        if conn:
            conn.close()

    return render_template(
        'admin/purchases.html',
        purchases=purchases_list,
        page=page,
        total_pages=total_pages,
        total_purchases=total_purchases,
        per_page=per_page,
        q_id=q_id,
        q_name=q_name,
        q_phone=q_phone,
        q_date=q_date,
        sort_by=sort_by
    )
