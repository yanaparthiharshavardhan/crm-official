from datetime import datetime
from app.models.user import db

class LeadStatus:
    NEW = 'New'
    CONTACTED = 'Contacted'
    QUALIFIED = 'Qualified'
    UNQUALIFIED = 'Unqualified'
    CONVERTED = 'Converted'
    LOST = 'Lost'

    ALL = [NEW, CONTACTED, QUALIFIED, UNQUALIFIED, CONVERTED, LOST]
    OPEN_STATUSES = [NEW, CONTACTED, QUALIFIED]
    CHOICES = [(s, s) for s in ALL]

class LeadPriority:
    LOW = 'Low'
    MEDIUM = 'Medium'
    HIGH = 'High'
    CHOICES = [(LOW, 'Low'), (MEDIUM, 'Medium'), (HIGH, 'High')]

class LeadSource:
    WEBSITE = 'Website'
    REFERRAL = 'Referral'
    COLD_CALL = 'Cold Call'
    CAMPAIGN = 'Campaign'
    PARTNER = 'Partner'
    OTHER = 'Other'
    CHOICES = [(WEBSITE, 'Website'), (REFERRAL, 'Referral'), (COLD_CALL, 'Cold Call'), 
               (CAMPAIGN, 'Campaign'), (PARTNER, 'Partner'), (OTHER, 'Other')]

class Lead(db.Model):
    __tablename__ = 'leads'

    id = db.Column(db.Integer, primary_key=True)
    lead_code = db.Column(db.String(20), unique=True, nullable=False, index=True)
    lead_name = db.Column(db.String(100), nullable=False, index=True)
    email = db.Column(db.String(120), nullable=False, index=True)
    phone = db.Column(db.String(20), nullable=False, index=True)
    company_name = db.Column(db.String(100), nullable=False)
    source = db.Column(db.String(50), nullable=False, default=LeadSource.WEBSITE)
    status = db.Column(db.String(50), nullable=False, default=LeadStatus.NEW)
    priority = db.Column(db.String(20), nullable=False, default=LeadPriority.MEDIUM)
    expected_value = db.Column(db.Float, nullable=False, default=0.0)
    notes = db.Column(db.Text, nullable=True)
    
    assigned_to_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    converted_customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=True)
    converted_opportunity_id = db.Column(db.Integer, db.ForeignKey('opportunities.id'), nullable=True)
    
    created_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    modified_date = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    converted_customer = db.relationship('Customer', foreign_keys=[converted_customer_id], lazy=True)
    converted_opportunity = db.relationship('Opportunity', foreign_keys=[converted_opportunity_id], lazy=True)
    followups = db.relationship('FollowUp', backref='lead', cascade='all, delete-orphan', lazy=True)
    activities = db.relationship('Activity', backref='lead', cascade='all, delete-orphan', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'lead_code': self.lead_code,
            'lead_name': self.lead_name,
            'email': self.email,
            'phone': self.phone,
            'company_name': self.company_name,
            'source': self.source,
            'status': self.status,
            'priority': self.priority,
            'expected_value': self.expected_value,
            'notes': self.notes,
            'assigned_to_id': self.assigned_to_id,
            'assigned_to_name': self.assigned_to.name if self.assigned_to else None,
            'converted_customer_id': self.converted_customer_id,
            'created_date': self.created_date.isoformat() if self.created_date else None,
            'modified_date': self.modified_date.isoformat() if self.modified_date else None
        }

    def __repr__(self):
        return f'<Lead {self.lead_code} - {self.lead_name}>'

