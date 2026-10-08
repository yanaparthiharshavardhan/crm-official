from datetime import datetime
from app.models.user import db

class Customer(db.Model):
    __tablename__ = 'customers'

    id = db.Column(db.Integer, primary_key=True)
    customer_code = db.Column(db.String(20), unique=True, nullable=False, index=True)
    customer_name = db.Column(db.String(100), nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(20), unique=True, nullable=False, index=True)
    company_name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(255), nullable=True)
    city = db.Column(db.String(50), nullable=True)
    state = db.Column(db.String(50), nullable=True)
    status = db.Column(db.String(20), default='Active', nullable=False) # Active, Inactive
    notes = db.Column(db.Text, nullable=True)
    
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    created_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    modified_date = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    opportunities = db.relationship('Opportunity', backref='customer', cascade='all, delete-orphan', lazy=True)
    followups = db.relationship('FollowUp', backref='customer', cascade='all, delete-orphan', lazy=True)
    activities = db.relationship('Activity', backref='customer', cascade='all, delete-orphan', lazy=True)
    created_by = db.relationship('User', foreign_keys=[created_by_id], lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'customer_code': self.customer_code,
            'customer_name': self.customer_name,
            'email': self.email,
            'phone': self.phone,
            'company_name': self.company_name,
            'address': self.address,
            'city': self.city,
            'state': self.state,
            'status': self.status,
            'notes': self.notes,
            'owner_id': self.owner_id,
            'owner_name': self.owner.name if self.owner else None,
            'created_date': self.created_date.isoformat() if self.created_date else None,
            'modified_date': self.modified_date.isoformat() if self.modified_date else None
        }

    def __repr__(self):
        return f'<Customer {self.customer_code} - {self.customer_name}>'

