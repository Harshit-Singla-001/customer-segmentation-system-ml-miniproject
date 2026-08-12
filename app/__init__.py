import os
from flask import Flask
from config import Config

def format_inr(value):
    """Format monetary numbers into Indian Rupee style (e.g. ₹1,25,000.00)"""
    if value is None:
        return "₹0.00"
    try:
        val = float(value)
    except (ValueError, TypeError):
        return "₹0.00"
    
    is_negative = val < 0
    val = abs(val)
    s = f"{val:.2f}"
    parts = s.split('.')
    integer_part, decimal_part = parts[0], parts[1]
    
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
    return f"{prefix}{formatted_int}.{decimal_part}"

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Register Jinja template filter for Indian Rupee currency formatting
    app.jinja_env.filters['inr'] = format_inr

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

    return app
