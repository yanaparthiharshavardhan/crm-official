from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class Role:
    ADMIN = 'Admin'
    MANAGER = 'Manager'
    SALES_EXECUTIVE = 'SalesExecutive'
    
    CHOICES = [
        (ADMIN, 'Administrator'),
        (MANAGER, 'Sales Manager'),
        (SALES_EXECUTIVE, 'Sales Executive')
    ]

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), nullable=False, default=Role.SALES_EXECUTIVE)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    failed_login_count = db.Column(db.Integer, default=0, nullable=False)
    lockout_end = db.Column(db.DateTime, nullable=True)
    created_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    assigned_customers = db.relationship('Customer', foreign_keys='Customer.owner_id', backref='owner', lazy=True)
    assigned_leads = db.relationship('Lead', foreign_keys='Lead.assigned_to_id', backref='assigned_to', lazy=True)
    assigned_opportunities = db.relationship('Opportunity', foreign_keys='Opportunity.assigned_to_id', backref='assigned_to', lazy=True)
    assigned_followups = db.relationship('FollowUp', foreign_keys='FollowUp.assigned_to_id', backref='assigned_to', lazy=True)
    assigned_activities = db.relationship('Activity', foreign_keys='Activity.assigned_to_id', backref='assigned_to', lazy=True)
    audit_logs = db.relationship('AuditLog', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_locked_out(self):
        if self.lockout_end:
            now_val = datetime.now(timezone.utc) if self.lockout_end.tzinfo else datetime.utcnow()
            return self.lockout_end > now_val
        return False

    @property
    def is_admin(self):
        return self.role == Role.ADMIN

    @property
    def is_manager(self):
        return self.role == Role.MANAGER

    @property
    def is_sales_executive(self):
        return self.role == Role.SALES_EXECUTIVE

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'role': self.role,
            'is_active': self.is_active,
            'is_locked_out': self.is_locked_out,
            'created_date': self.created_date.isoformat() if self.created_date else None
        }

    def __repr__(self):
        return f'<User {self.email} ({self.role})>'
