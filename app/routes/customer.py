from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from app.db.connection import execute_query, get_db_connection

customer_bp = Blueprint('customer', __name__)

@customer_bp.route('/products')
def products():
    products_list = execute_query("SELECT * FROM products ORDER BY category, name", fetch_all=True) or []
    categories = sorted(list(set(p['category'] for p in products_list if p.get('category'))))
    return render_template('customer/products.html', categories=categories, products=products_list)

@customer_bp.route('/check-customer')
def check_customer():
    """AJAX endpoint to check if a customer already exists by mobile number."""
    phone = request.args.get('phone', '').strip()
    if not phone:
        return jsonify({'exists': False})

    customer = execute_query(
        "SELECT customer_id, name, age, gender, city, income FROM customers WHERE phone = %s",
        (phone,),
        fetch_one=True
    )
    if customer:
        return jsonify({
            'exists': True,
            'name': customer['name'],
            'age': customer.get('age'),
            'gender': customer.get('gender') or '',
            'city': customer.get('city') or '',
            'income': float(customer['income']) if customer.get('income') else None
        })
    return jsonify({'exists': False})

@customer_bp.route('/add-to-cart', methods=['POST'])
def add_to_cart():
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json or request.form.get('is_ajax') == '1'
    product_id = request.form.get('product_id', type=int)
    if not product_id and request.is_json:
        product_id = request.json.get('product_id')
    quantity = request.form.get('quantity', type=int, default=1)
    if request.is_json and 'quantity' in request.json:
        quantity = int(request.json['quantity'])
    redirect_to = request.form.get('redirect_to', 'main.index')

    if not product_id or quantity <= 0:
        if is_ajax:
            return jsonify({'success': False, 'message': 'Invalid product selection.'}), 400
        flash("Invalid product selection.", "warning")
        return redirect(url_for(redirect_to))

    # Check stock
    prod = execute_query("SELECT name, stock_quantity, status FROM products WHERE product_id = %s", (product_id,), fetch_one=True)
    if not prod or prod['status'] == 'Out of Stock' or prod['stock_quantity'] <= 0:
        if is_ajax:
            return jsonify({'success': False, 'message': 'Item is currently out of stock.'}), 400
        flash("Sorry, this item is currently out of stock.", "danger")
        return redirect(url_for(redirect_to))

    cart = session.get('cart', {})
    str_pid = str(product_id)
    cart[str_pid] = cart.get(str_pid, 0) + quantity
    session['cart'] = cart
    total_cart_count = sum(cart.values())

    if is_ajax:
        return jsonify({
            'success': True,
            'product_id': product_id,
            'product_name': prod['name'],
            'qty_in_cart': cart[str_pid],
            'total_cart_count': total_cart_count,
            'message': f"'{prod['name']}' added to cart!"
        })

    flash("Item added to cart!", "success")
    return redirect(url_for(redirect_to))


@customer_bp.route('/remove-from-cart', methods=['POST'])
def remove_from_cart():
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json or request.form.get('is_ajax') == '1'
    product_id = request.form.get('product_id', type=int)
    if not product_id and request.is_json:
        product_id = request.json.get('product_id')

    cart = session.get('cart', {})
    str_pid = str(product_id)

    if str_pid in cart:
        del cart[str_pid]
        session['cart'] = cart

    total_cart_count = sum(cart.values())

    if is_ajax:
        return jsonify({
            'success': True,
            'product_id': product_id,
            'qty_in_cart': 0,
            'total_cart_count': total_cart_count,
            'message': 'Item removed from cart.'
        })

    flash("Item removed from cart.", "info")
    return redirect(url_for('customer.cart'))

@customer_bp.route('/cart')
def cart():
    cart_dict = session.get('cart', {})
    cart_items = []
    total_amount = 0.0

    if cart_dict:
        product_ids = [int(pid) for pid in cart_dict.keys()]
        if product_ids:
            format_strings = ','.join(['%s'] * len(product_ids))
            query = f"SELECT * FROM products WHERE product_id IN ({format_strings})"
            products_list = execute_query(query, tuple(product_ids), fetch_all=True) or []
            
            for p in products_list:
                qty = cart_dict.get(str(p['product_id']), 0)
                subtotal = float(p['price']) * qty
                total_amount += subtotal
                cart_items.append({
                    'product_id': p['product_id'],
                    'name': p['name'],
                    'category': p['category'],
                    'price': float(p['price']),
                    'quantity': qty,
                    'subtotal': subtotal,
                    'stock_quantity': p['stock_quantity']
                })

    return render_template('customer/cart.html', cart_items=cart_items, total_amount=total_amount)

@customer_bp.route('/update-cart', methods=['POST'])
def update_cart():
    product_id = request.form.get('product_id', type=int)
    action = request.form.get('action') # 'increase', 'decrease', 'remove'

    cart = session.get('cart', {})
    str_pid = str(product_id)

    if str_pid in cart:
        if action == 'increase':
            cart[str_pid] += 1
        elif action == 'decrease':
            cart[str_pid] -= 1
            if cart[str_pid] <= 0:
                del cart[str_pid]
        elif action == 'remove':
            del cart[str_pid]
        session['cart'] = cart
        flash("Cart updated.", "info")

    return redirect(url_for('customer.cart'))

@customer_bp.route('/checkout', methods=['POST'])
def checkout():
    cart_dict = session.get('cart', {})
    if not cart_dict:
        flash("Your cart is empty.", "warning")
        return redirect(url_for('main.index'))

    phone = request.form.get('phone', '').strip()
    clean_phone = ''.join(c for c in phone if c.isdigit())
    if not clean_phone or len(clean_phone) != 10 or clean_phone[0] not in ('6', '7', '8', '9'):
        flash("Please enter a valid 10-digit Indian mobile number starting with 6, 7, 8, or 9.", "warning")
        return redirect(url_for('customer.cart'))
    phone = clean_phone
    name = request.form.get('name', '').strip()
    age = request.form.get('age', type=int)
    gender = request.form.get('gender', '').strip() or 'Other'
    city = request.form.get('city', '').strip() or None
    income = request.form.get('income', '').strip()

    income_val = None
    if income:
        try:
            income_val = float(income)
            if income_val < 0 or income_val > 100000000:
                income_val = None
        except ValueError:
            income_val = None

    conn = None
    try:
        # Optimized single database connection block for the entire checkout transaction
        conn = get_db_connection(with_database=True)
        with conn.cursor() as cursor:
            # 1. Customer check/insert
            cursor.execute("SELECT customer_id, name, age, gender, city, income FROM customers WHERE phone = %s", (phone,))
            customer = cursor.fetchone()

            if customer:
                customer_id = customer['customer_id']
                cust_name = name or customer['name']
                cursor.execute(
                    "UPDATE customers SET city = COALESCE(%s, city), income = COALESCE(%s, income), age = COALESCE(%s, age), gender = COALESCE(%s, gender) WHERE customer_id = %s",
                    (city, income_val, age, gender, customer_id)
                )
            else:
                if not name:
                    name = f"Customer {phone[-4:]}"
                synth_email = f"user_{phone}@customer.local"
                cursor.execute("""
                    INSERT INTO customers (name, email, phone, age, gender, city, income, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, 'Active')
                """, (name, synth_email, phone, age, gender, city, income_val))
                customer_id = cursor.lastrowid
                cust_name = name

            session['customer_id'] = customer_id
            session['customer_name'] = cust_name

            # 2. Fetch products in cart
            product_ids = [int(pid) for pid in cart_dict.keys()]
            format_strings = ','.join(['%s'] * len(product_ids))
            query = f"SELECT product_id, price, stock_quantity FROM products WHERE product_id IN ({format_strings})"
            cursor.execute(query, tuple(product_ids))
            products_list = cursor.fetchall() or []

            total_amount = 0.0
            order_items = []
            for p in products_list:
                qty = cart_dict.get(str(p['product_id']), 0)
                unit_price = float(p['price'])
                subtotal = unit_price * qty
                total_amount += subtotal
                order_items.append((p['product_id'], qty, unit_price, subtotal))

            # 3. Insert purchase transaction header by dynamically calculating IST from device system clock
            from app import get_current_ist_time
            now_ist_str = get_current_ist_time().strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute("""
                INSERT INTO purchases (customer_id, purchase_date, total_amount, status)
                VALUES (%s, %s, %s, 'Completed')
            """, (customer_id, now_ist_str, total_amount))
            purchase_id = cursor.lastrowid

            # 4. Insert items & decrement stock count
            for pid, qty, unit_price, subtotal in order_items:
                cursor.execute("""
                    INSERT INTO purchase_items (purchase_id, product_id, quantity, unit_price, subtotal)
                    VALUES (%s, %s, %s, %s, %s)
                """, (purchase_id, pid, qty, unit_price, subtotal))
                
                cursor.execute("""
                    UPDATE products 
                    SET stock_quantity = GREATEST(0, stock_quantity - %s),
                        status = CASE WHEN (stock_quantity - %s) <= 0 THEN 'Out of Stock' ELSE status END
                    WHERE product_id = %s
                """, (qty, qty, pid))

            conn.commit()

        # Clear cart session
        session['cart'] = {}

        # 5. Instant K-Means Cluster Assignment for new or returning customer
        cluster_name = None
        try:
            from app.ml.clustering import classify_single_customer
            cluster_label, cluster_name = classify_single_customer(customer_id)
        except Exception as e:
            print(f"[ML] Error classifying customer #{customer_id}: {e}")

        segment_info = f" • Customer Segment: {cluster_name}" if cluster_name else ""
        flash(f"Order #{purchase_id} placed successfully for {name}! Total: ₹{total_amount:,.2f}{segment_info}", "success")
        return redirect(url_for('main.index'))

    except Exception as e:
        if conn:
            conn.rollback()
        flash(f"Error placing order: {str(e)}", "danger")
        return redirect(url_for('customer.cart'))
    finally:
        if conn:
            conn.close()
