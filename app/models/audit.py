from datetime import datetime
from app.models.user import db

class AuditAction:
    LOGIN = 'Login'
    FAILED_LOGIN = 'Failed Login'
    LOGOUT = 'Logout'
    CREATE = 'Create'
    UPDATE = 'Update'
    DELETE = 'Delete'
    ROLE_CHANGE = 'Role Change'
    SECURITY = 'Security'
    CONVERT = 'Convert'
    LOCKOUT = 'Lockout'
    UNLOCK = 'Unlock'

    ALL = [LOGIN, FAILED_LOGIN, LOGOUT, CREATE, UPDATE, DELETE, ROLE_CHANGE, SECURITY, CONVERT, LOCKOUT, UNLOCK]

class AuditLog(db.Model):
    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    user_email = db.Column(db.String(120), nullable=True) # Fallback if user deleted
    action = db.Column(db.String(50), nullable=False, index=True)
    entity_name = db.Column(db.String(100), nullable=False, index=True) # Module/Entity: Customer, Lead, Opportunity, Auth, User, FollowUp, Activity
    record_id = db.Column(db.String(50), nullable=True)
    old_value = db.Column(db.Text, nullable=True)
    new_value = db.Column(db.Text, nullable=True)
    details = db.Column(db.Text, nullable=True)
    result = db.Column(db.String(20), default='Success', nullable=False) # Success, Failure
    ip_address = db.Column(db.String(50), nullable=True)
    created_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'user_name': self.user.name if self.user else (self.user_email or 'System/Anonymous'),
            'action': self.action,
            'entity_name': self.entity_name,
            'record_id': self.record_id,
            'old_value': self.old_value,
            'new_value': self.new_value,
            'details': self.details,
            'result': self.result,
            'ip_address': self.ip_address,
            'created_date': self.created_date.isoformat() if self.created_date else None
        }

    def __repr__(self):
        return f'<AuditLog {self.id} - {self.action} on {self.entity_name}>'

