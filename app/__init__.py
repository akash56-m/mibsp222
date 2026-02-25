"""
MIBSP Flask Application Factory
Creates and configures the Flask application with all extensions.
"""
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from config import config

# Initialize extensions (no app yet)
db = SQLAlchemy()
migrate = Migrate()
csrf = CSRFProtect()


def create_app(config_name=None):
    """
    Application factory pattern - creates and configures Flask app.
    """

    if config_name is None:
        import os
        config_name = os.environ.get('FLASK_ENV', 'default')

    app = Flask(
        __name__,
        instance_relative_config=True,
        template_folder='templates',
        static_folder='static'
    )

    # Load configuration
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)

    # 🔥 IMPORTANT: Import models BEFORE create_all()
    from app import models

    # 🔥 Create tables (for Render / PostgreSQL)
    with app.app_context():
        db.create_all()

    # Register blueprints
    from app.routes.public import public_bp
    from app.routes.auth import auth_bp
    from app.routes.officer import officer_bp
    from app.routes.admin import admin_bp

    app.register_blueprint(public_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(officer_bp, url_prefix='/officer')
    app.register_blueprint(admin_bp, url_prefix='/admin')

    # Register error handlers
    register_error_handlers(app)

    # Register template filters
    register_template_filters(app)

    return app


def register_error_handlers(app):

    @app.errorhandler(403)
    def forbidden(error):
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def not_found(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('errors/500.html'), 500

    @app.errorhandler(413)
    def too_large(error):
        return render_template('errors/413.html'), 413


def register_template_filters(app):

    @app.template_filter('format_datetime')
    def format_datetime(value, format='%d %b %Y, %I:%M %p'):
        if value is None:
            return 'N/A'
        return value.strftime(format)

    @app.template_filter('status_badge')
    def status_badge(status):
        badges = {
            'Pending': 'badge-pending',
            'Under Review': 'badge-review',
            'Action Taken': 'badge-action',
            'Closed': 'badge-closed'
        }
        return badges.get(status, 'badge-secondary')

    @app.template_filter('status_icon')
    def status_icon(status):
        icons = {
            'Pending': 'clock',
            'Under Review': 'search',
            'Action Taken': 'tools',
            'Closed': 'check-circle'
        }
        return icons.get(status, 'circle')