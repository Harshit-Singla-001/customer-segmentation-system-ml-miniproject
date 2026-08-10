import os
from flask import Flask
from config import Config

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Ensure upload directory exists
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
