from datetime import datetime, date
from app.models.user import db

class OpportunityStage:
    QUALIFICATION = 'Qualification'
    PROPOSAL = 'Proposal'
    NEGOTIATION = 'Negotiation'
    WON = 'Won'
    LOST = 'Lost'

    ALL = [QUALIFICATION, PROPOSAL, NEGOTIATION, WON, LOST]
    CHOICES = [(s, s) for s in ALL]
    
    STAGE_PROBABILITY_MAP = {
        QUALIFICATION: 20,
        PROPOSAL: 50,
        NEGOTIATION: 80,
        WON: 100,
        LOST: 0
    }

class OpportunityStatus:
    OPEN = 'Open'
    WON = 'Won'
    LOST = 'Lost'
    CHOICES = [(OPEN, 'Open'), (WON, 'Won'), (LOST, 'Lost')]

class Opportunity(db.Model):
    __tablename__ = 'opportunities'

    id = db.Column(db.Integer, primary_key=True)
    opportunity_code = db.Column(db.String(20), unique=True, nullable=False, index=True)
    opportunity_name = db.Column(db.String(150), nullable=False, index=True)
    
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=True)
    lead_id = db.Column(db.Integer, db.ForeignKey('leads.id'), nullable=True)
    
    amount = db.Column(db.Float, nullable=False)
    stage = db.Column(db.String(50), nullable=False, default=OpportunityStage.QUALIFICATION)
    probability = db.Column(db.Integer, nullable=False, default=20) # 0 to 100
    expected_close_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), nullable=False, default=OpportunityStatus.OPEN) # Open, Won, Lost
    source = db.Column(db.String(50), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    
    assigned_to_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    modified_date = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    followups = db.relationship('FollowUp', backref='opportunity', cascade='all, delete-orphan', lazy=True)
    lead_rel = db.relationship('Lead', foreign_keys=[lead_id], lazy=True)

    @property
    def weighted_amount(self):
        """Derives weighted pipeline: Amount * Probability / 100"""
        if self.amount and self.probability is not None:
            return round((self.amount * self.probability) / 100.0, 2)
        return 0.0

    def to_dict(self):
        return {
            'id': self.id,
            'opportunity_code': self.opportunity_code,
            'opportunity_name': self.opportunity_name,
            'customer_id': self.customer_id,
            'customer_name': self.customer.customer_name if self.customer else None,
            'lead_id': self.lead_id,
            'amount': self.amount,
            'stage': self.stage,
            'probability': self.probability,
            'weighted_amount': self.weighted_amount,
            'expected_close_date': self.expected_close_date.isoformat() if self.expected_close_date else None,
            'status': self.status,
            'source': self.source,
            'notes': self.notes,
            'assigned_to_id': self.assigned_to_id,
            'assigned_to_name': self.assigned_to.name if self.assigned_to else None,
            'created_date': self.created_date.isoformat() if self.created_date else None,
            'modified_date': self.modified_date.isoformat() if self.modified_date else None
        }

    def __repr__(self):
        return f'<Opportunity {self.opportunity_code} - {self.opportunity_name}>'

