from flask import Blueprint, render_template, flash, redirect, url_for
from app.db.connection import init_db, get_db_connection, execute_query

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    categories = []
    products_list = []
    try:
        # Optimized single query: fetch products and extract unique categories in Python
        products_list = execute_query("SELECT * FROM products ORDER BY category, name", fetch_all=True) or []
        categories = sorted(list(set(p['category'] for p in products_list if p.get('category'))))
    except Exception as e:
        flash(f"Database warning: {str(e)}", "warning")

    return render_template('index.html', categories=categories, products=products_list)


@main_bp.route('/init-db', methods=['POST', 'GET'])
def initialize_database():
    success, message = init_db()
    if success:
        flash(f"Database status: {message}", "success")
    else:
        flash(f"Database error: {message}", "danger")
    return redirect(url_for('main.index'))
