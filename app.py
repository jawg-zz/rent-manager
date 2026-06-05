import os
from datetime import datetime
from flask import Flask, redirect, url_for, session
from flask_login import LoginManager, current_user
from models import db, User

login_manager = LoginManager()


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-me')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///data/rent.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'warning'

    @login_manager.user_loader
    def load_user(user_id):
        try:
            return User.query.get(int(user_id))
        except Exception:
            return None

    # Register blueprints
    from routes.auth import auth_bp
    from routes.dashboard import dashboard_bp
    from routes.properties import properties_bp
    from routes.tenants import tenants_bp
    from routes.leases import leases_bp
    from routes.payments import payments_bp
    from routes.reports import reports_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(properties_bp, url_prefix='/properties')
    app.register_blueprint(tenants_bp, url_prefix='/tenants')
    app.register_blueprint(leases_bp, url_prefix='/leases')
    app.register_blueprint(payments_bp, url_prefix='/payments')
    app.register_blueprint(reports_bp, url_prefix='/reports')

    # Context processor
    @app.context_processor
    def inject_globals():
        demo_mode = os.environ.get('DEMO_MODE', 'false').lower() == 'true'
        return dict(demo_mode=demo_mode, now=datetime.utcnow())

    # Create tables + seed
    with app.app_context():
        from models import Property, Unit, Tenant, Lease, Payment, MaintenanceRequest, AuditLog
        db.create_all()
        if User.query.count() == 0:
            demo_mode = os.environ.get('DEMO_MODE', 'false').lower() == 'true'
            if demo_mode:
                from seed import seed_demo_data
                seed_demo_data(db, User, Property, Unit, Tenant, Lease, Payment)

    # Health check for Dokploy
    @app.route('/health')
    def health():
        return 'OK', 200

    # Root redirect
    @app.route('/')
    def index():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard.index'))
        return redirect(url_for('auth.login'))

    return app
