from datetime import datetime, date
from app.models.user import db

class FollowUpStatus:
    PLANNED = 'Planned'
    COMPLETED = 'Completed'
    MISSED = 'Missed'
    CANCELLED = 'Cancelled'
    CHOICES = [(PLANNED, 'Planned'), (COMPLETED, 'Completed'), (MISSED, 'Missed'), (CANCELLED, 'Cancelled')]

class FollowUpType:
    CALL = 'Call'
    MEETING = 'Meeting'
    EMAIL = 'Email'
    TASK = 'Task'
    CHOICES = [(CALL, 'Call'), (MEETING, 'Meeting'), (EMAIL, 'Email'), (TASK, 'Task')]

class FollowUp(db.Model):
    __tablename__ = 'followups'

    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.String(150), nullable=False)
    followup_type = db.Column(db.String(50), nullable=False, default=FollowUpType.CALL)
    followup_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(50), nullable=False, default=FollowUpStatus.PLANNED)
    remarks = db.Column(db.Text, nullable=True)
    
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=True)
    lead_id = db.Column(db.Integer, db.ForeignKey('leads.id'), nullable=True)
    opportunity_id = db.Column(db.Integer, db.ForeignKey('opportunities.id'), nullable=True)
    assigned_to_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    created_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    modified_date = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    @property
    def is_overdue(self):
        if self.status == FollowUpStatus.PLANNED and self.followup_date < date.today():
            return True
        return False

    @property
    def related_entity_display(self):
        if self.customer:
            return f"Customer: {self.customer.customer_name}"
        elif self.lead:
            return f"Lead: {self.lead.lead_name}"
        elif self.opportunity:
            return f"Opportunity: {self.opportunity.opportunity_name}"
        return "General"

    def to_dict(self):
        return {
            'id': self.id,
            'subject': self.subject,
            'followup_type': self.followup_type,
            'followup_date': self.followup_date.isoformat() if self.followup_date else None,
            'status': self.status,
            'is_overdue': self.is_overdue,
            'remarks': self.remarks,
            'customer_id': self.customer_id,
            'customer_name': self.customer.customer_name if self.customer else None,
            'lead_id': self.lead_id,
            'lead_name': self.lead.lead_name if self.lead else None,
            'opportunity_id': self.opportunity_id,
            'opportunity_name': self.opportunity.opportunity_name if self.opportunity else None,
            'assigned_to_id': self.assigned_to_id,
            'assigned_to_name': self.assigned_to.name if self.assigned_to else None,
            'created_date': self.created_date.isoformat() if self.created_date else None
        }

    def __repr__(self):
        return f'<FollowUp {self.id} - {self.subject}>'

