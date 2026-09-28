import os
from flask import Flask
from config import Config

def format_inr(value):
    """Format monetary numbers into clean Indian Rupee style (e.g. ₹1,25,000) without decimal points."""
    if value is None:
        return "₹0"
    try:
        val = float(value)
    except (ValueError, TypeError):
        return "₹0"

    is_negative = val < 0
    val = round(abs(val))
    integer_part = str(int(val))

    if len(integer_part) <= 3:
        formatted_int = integer_part
    else:
        last_three = integer_part[-3:]
        remaining = integer_part[:-3]
        groups = []
        while len(remaining) > 2:
            groups.insert(0, remaining[-2:])
            remaining = remaining[:-2]
        if remaining:
            groups.insert(0, remaining)
        formatted_int = ','.join(groups) + ',' + last_three

    prefix = "-₹" if is_negative else "₹"
    return f"{prefix}{formatted_int}"

from datetime import datetime, timezone, timedelta

# Indian Standard Time (IST — UTC+5:30) target timezone
IST = timezone(timedelta(hours=5, minutes=30))

def get_current_ist_time():
    """
    Dynamically accesses the host device's local system clock and timezone,
    then dynamically calculates and returns the current Indian Standard Time (IST).
    """
    device_now = datetime.now().astimezone()
    return device_now.astimezone(IST)

def format_ist(value, fmt="%d %b %Y, %I:%M %p"):
    """
    Dynamically converts device/database datetime objects into Indian Standard Time (Asia/Kolkata).
    """
    if not value:
        return "—"

    if isinstance(value, str):
        try:
            value = datetime.strptime(value.split('.')[0], "%Y-%m-%d %H:%M:%S")
        except Exception:
            try:
                value = datetime.fromisoformat(value)
            except Exception:
                return value

    if isinstance(value, datetime):
        # Dynamically inspect device local timezone if naive, then convert to IST
        if value.tzinfo is None:
            device_dt = value.astimezone()
            ist_dt = device_dt.astimezone(IST)
            return ist_dt.strftime(fmt)
        else:
            return value.astimezone(IST).strftime(fmt)

    return str(value)

import threading

def _run_warmup(app):
    """
    Background worker that runs immediately on server startup to preload
    heavy ML dependencies, compile templates, and warm dashboard caches in RAM.
    """
    with app.app_context():
        try:
            from app.db.connection import ensure_db_indexes
            ensure_db_indexes()

            from app.ml.clustering import load_or_train_model, get_dashboard_ml_data
            load_or_train_model()
            get_dashboard_ml_data()

            # Pre-compile Jinja templates for zero first-render latency
            app.jinja_env.get_template('admin/dashboard.html')
            app.jinja_env.get_template('admin/login.html')
            app.jinja_env.get_template('admin/customers.html')
            app.jinja_env.get_template('admin/products.html')
            app.jinja_env.get_template('admin/purchases.html')

            print("[WARMUP] Admin dashboard & ML components preloaded successfully in background.")
        except Exception as e:
            print(f"[WARMUP] Background preload note: {e}")

def start_background_warmup(app):
    t = threading.Thread(target=_run_warmup, args=(app,), daemon=True, name="AdminPreloadWorker")
    t.start()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Register Jinja template filters
    app.jinja_env.filters['inr'] = format_inr
    app.jinja_env.filters['ist'] = format_ist

    # Ensure upload & export directories exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(os.path.join(app.config['BASE_DIR'], 'exports'), exist_ok=True)

    # Register blueprints
    from app.routes.main import main_bp
    from app.routes.customer import customer_bp
    from app.routes.admin import admin_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(customer_bp, url_prefix='/customer')
    app.register_blueprint(admin_bp, url_prefix='/admin')

    # Automatically verify SQLite/MySQL database and auto-import dataset if not yet inserted
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true' or not app.debug:
        with app.app_context():
            try:
                from app.db.connection import check_and_auto_import_db
                check_and_auto_import_db()
            except Exception as e:
                print(f"[AUTO-DB] Startup DB check info: {e}")

        # Launch background preloading for admin dashboard
        start_background_warmup(app)

    return app
