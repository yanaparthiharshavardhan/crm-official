from app.routes.auth_routes import auth_bp
from app.routes.dashboard_routes import dashboard_bp
from app.routes.customer_routes import customer_bp
from app.routes.lead_routes import lead_bp
from app.routes.opportunity_routes import opportunity_bp
from app.routes.followup_routes import followup_bp
from app.routes.activity_routes import activity_bp
from app.routes.user_routes import user_bp
from app.routes.report_routes import report_bp
from app.routes.audit_routes import audit_bp
from app.routes.api_routes import api_bp

__all__ = [
    'auth_bp',
    'dashboard_bp',
    'customer_bp',
    'lead_bp',
    'opportunity_bp',
    'followup_bp',
    'activity_bp',
    'user_bp',
    'report_bp',
    'audit_bp',
    'api_bp'
]

