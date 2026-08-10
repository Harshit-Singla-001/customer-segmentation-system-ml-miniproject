from flask import Blueprint, render_template, flash, redirect, url_for
from app.db.connection import init_db, get_db_connection

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    db_connected = False
    try:
        conn = get_db_connection()
        conn.close()
        db_connected = True
    except Exception:
        db_connected = False

    return render_template('index.html', db_connected=db_connected)

@main_bp.route('/init-db', methods=['POST', 'GET'])
def initialize_database():
    success, message = init_db()
    if success:
        flash(f"Database status: {message}", "success")
    else:
        flash(f"Database error: {message}", "danger")
    return redirect(url_for('main.index'))
