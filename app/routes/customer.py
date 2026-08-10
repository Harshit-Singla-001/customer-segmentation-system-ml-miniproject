from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.db.connection import execute_query

customer_bp = Blueprint('customer', __name__)

@customer_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        income = request.form.get('income', '').strip()
        age = request.form.get('age', '').strip()
        gender = request.form.get('gender', '').strip()

        if not name or not email or not phone:
            flash("Name, Email, and Phone number are required fields.", "warning")
            return render_template('customer/register.html')

        income_val = float(income) if income else None
        age_val = int(age) if age else None

        try:
            query = """
                INSERT INTO customers (name, email, phone, income, age, gender)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            customer_id = execute_query(query, (name, email, phone, income_val, age_val, gender), commit=True)
            session['customer_id'] = customer_id
            session['customer_name'] = name
            flash(f"Welcome {name}! Your registration was successful.", "success")
            return redirect(url_for('customer.products'))
        except Exception as e:
            flash(f"Registration failed: {str(e)}", "danger")

    return render_template('customer/register.html')

@customer_bp.route('/products')
def products():
    if 'customer_id' not in session:
        flash("Please enter your details to proceed to the store.", "info")
        return redirect(url_for('customer.register'))

    products_list = execute_query("SELECT * FROM products ORDER BY category, name", fetch_all=True) or []
    return render_template('customer/products.html', products=products_list)

@customer_bp.route('/add-to-cart', methods=['POST'])
def add_to_cart():
    product_id = request.form.get('product_id', type=int)
    quantity = request.form.get('quantity', type=int, default=1)

    if not product_id or quantity <= 0:
        flash("Invalid product selection.", "warning")
        return redirect(url_for('customer.products'))

    cart = session.get('cart', {})
    str_pid = str(product_id)
    cart[str_pid] = cart.get(str_pid, 0) + quantity
    session['cart'] = cart
    flash("Product added to cart!", "success")
    return redirect(url_for('customer.products'))

@customer_bp.route('/cart')
def cart():
    if 'customer_id' not in session:
        return redirect(url_for('customer.register'))

    cart_dict = session.get('cart', {})
    cart_items = []
    total_amount = 0.0

    if cart_dict:
        product_ids = [int(pid) for pid in cart_dict.keys()]
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
                'price': float(p['price']),
                'quantity': qty,
                'subtotal': subtotal
            })

    return render_template('customer/cart.html', cart_items=cart_items, total_amount=total_amount)

@customer_bp.route('/checkout', methods=['POST'])
def checkout():
    customer_id = session.get('customer_id')
    cart_dict = session.get('cart', {})

    if not customer_id or not cart_dict:
        flash("Your cart is empty or customer session expired.", "warning")
        return redirect(url_for('customer.products'))

    try:
        # Fetch items
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

        # Insert purchase header
        p_query = "INSERT INTO purchases (customer_id, total_amount) VALUES (%s, %s)"
        purchase_id = execute_query(p_query, (customer_id, total_amount), commit=True)

        # Insert purchase items
        for pid, qty, unit_price, subtotal in order_items:
            item_query = """
                INSERT INTO purchase_items (purchase_id, product_id, quantity, unit_price, subtotal)
                VALUES (%s, %s, %s, %s, %s)
            """
            execute_query(item_query, (purchase_id, pid, qty, unit_price, subtotal), commit=True)

        # Clear cart
        session['cart'] = {}
        flash("Order placed successfully! Thank you for shopping.", "success")
        return redirect(url_for('customer.products'))

    except Exception as e:
        flash(f"Error processing order: {str(e)}", "danger")
        return redirect(url_for('customer.cart'))
