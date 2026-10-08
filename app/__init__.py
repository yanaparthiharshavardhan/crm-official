from datetime import datetime
from flask import Flask, render_template, request, jsonify
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from app.config import Config
from app.models import db, User

login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = "Please sign in to access this page."
login_manager.login_message_category = "warning"
csrf = CSRFProtect()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    # Register Blueprints
    from app.routes import (
        auth_bp, dashboard_bp, customer_bp, lead_bp,
        opportunity_bp, followup_bp, activity_bp,
        user_bp, report_bp, audit_bp, api_bp
    )

    csrf.exempt(api_bp)

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(customer_bp)
    app.register_blueprint(lead_bp)
    app.register_blueprint(opportunity_bp)
    app.register_blueprint(followup_bp)
    app.register_blueprint(activity_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(report_bp)
    app.register_blueprint(audit_bp)
    app.register_blueprint(api_bp)

    # Context processors
    @app.context_processor
    def inject_global_vars():
        return {
            'now': datetime.now(),
            'app_name': 'AcxiomCRM',
            'version': '1.0.0'
        }

    # Error handlers - Never leak internal details/traces to end users
    @app.errorhandler(400)
    def bad_request(error):
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Bad Request', 'message': 'The request was invalid or malformed.'}), 400
        return render_template('errors/400.html'), 400

    @app.errorhandler(403)
    def forbidden(error):
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Forbidden', 'message': 'You do not have permission to access this resource.'}), 403
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def page_not_found(error):
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Not Found', 'message': 'The requested resource does not exist.'}), 404
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Internal Server Error', 'message': 'An unexpected error occurred. Please try again later.'}), 500
        return render_template('errors/500.html'), 500

    return app
