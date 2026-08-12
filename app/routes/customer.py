from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.db.connection import execute_query

customer_bp = Blueprint('customer', __name__)

@customer_bp.route('/products')
def products():
    categories_raw = execute_query("SELECT DISTINCT category FROM products WHERE category IS NOT NULL AND category != '' ORDER BY category", fetch_all=True) or []
    categories = [c['category'] for c in categories_raw]
    products_list = execute_query("SELECT * FROM products ORDER BY category, name", fetch_all=True) or []
    return render_template('customer/products.html', categories=categories, products=products_list)

@customer_bp.route('/add-to-cart', methods=['POST'])
def add_to_cart():
    product_id = request.form.get('product_id', type=int)
    quantity = request.form.get('quantity', type=int, default=1)
    redirect_to = request.form.get('redirect_to', 'main.index')

    if not product_id or quantity <= 0:
        flash("Invalid product selection.", "warning")
        return redirect(url_for(redirect_to))

    # Check stock
    prod = execute_query("SELECT stock_quantity, status FROM products WHERE product_id = %s", (product_id,), fetch_one=True)
    if not prod or prod['status'] == 'Out of Stock' or prod['stock_quantity'] <= 0:
        flash("Sorry, this item is currently out of stock.", "danger")
        return redirect(url_for(redirect_to))

    cart = session.get('cart', {})
    str_pid = str(product_id)
    cart[str_pid] = cart.get(str_pid, 0) + quantity
    session['cart'] = cart
    flash("Item added to cart!", "success")
    return redirect(url_for(redirect_to))

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
    name = request.form.get('name', '').strip()
    city = request.form.get('city', '').strip() or 'Mumbai'
    income = request.form.get('income', '').strip()

    if not phone or not name:
        flash("Name and Phone Number are required to complete your purchase.", "warning")
        return redirect(url_for('customer.cart'))

    income_val = float(income) if income else None

    try:
        # Check if customer exists by phone number
        customer = execute_query("SELECT * FROM customers WHERE phone = %s", (phone,), fetch_one=True)
        
        if customer:
            customer_id = customer['customer_id']
            # Optionally update city or income if previously NULL
            if (not customer.get('city') and city) or (not customer.get('income') and income_val):
                execute_query("UPDATE customers SET city = COALESCE(city, %s), income = COALESCE(income, %s) WHERE customer_id = %s", (city, income_val, customer_id), commit=True)
        else:
            # Create new customer record
            synth_email = f"user_{phone.replace('+', '').replace(' ', '')}@customer.local"
            customer_id = execute_query("""
                INSERT INTO customers (name, email, phone, city, income, status)
                VALUES (%s, %s, %s, %s, %s, 'Active')
            """, (name, synth_email, phone, city, income_val), commit=True)

        session['customer_id'] = customer_id
        session['customer_name'] = name

        # Fetch products in cart
        product_ids = [int(pid) for pid in cart_dict.keys()]
        format_strings = ','.join(['%s'] * len(product_ids))
        query = f"SELECT * FROM products WHERE product_id IN ({format_strings})"
        products_list = execute_query(query, tuple(product_ids), fetch_all=True) or []

        total_amount = 0.0
        order_items = []
        for p in products_list:
            qty = cart_dict.get(str(p['product_id']), 0)
            unit_price = float(p['price'])
            subtotal = unit_price * qty
            total_amount += subtotal
            order_items.append((p['product_id'], qty, unit_price, subtotal))

        # Insert purchase transaction header
        purchase_id = execute_query("""
            INSERT INTO purchases (customer_id, total_amount, status)
            VALUES (%s, %s, 'Completed')
        """, (customer_id, total_amount), commit=True)

        # Insert item lines & adjust product stock
        for pid, qty, unit_price, subtotal in order_items:
            execute_query("""
                INSERT INTO purchase_items (purchase_id, product_id, quantity, unit_price, subtotal)
                VALUES (%s, %s, %s, %s, %s)
            """, (purchase_id, pid, qty, unit_price, subtotal), commit=True)
            
            # Decrement stock count
            execute_query("""
                UPDATE products 
                SET stock_quantity = GREATEST(0, stock_quantity - %s),
                    status = CASE WHEN (stock_quantity - %s) <= 0 THEN 'Out of Stock' ELSE status END
                WHERE product_id = %s
            """, (qty, qty, pid), commit=True)

        # Clear cart session
        session['cart'] = {}
        flash(f"Order #{purchase_id} placed successfully for {name}! Total: ₹{total_amount:,.2f}", "success")
        return redirect(url_for('main.index'))

    except Exception as e:
        flash(f"Error placing order: {str(e)}", "danger")
        return redirect(url_for('customer.cart'))
