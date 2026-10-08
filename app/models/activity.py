from datetime import datetime, date
from app.models.user import db

class ActivityType:
    CALL = 'Call'
    MEETING = 'Meeting'
    EMAIL = 'Email'
    TASK = 'Task'
    CHOICES = [(CALL, 'Call'), (MEETING, 'Meeting'), (EMAIL, 'Email'), (TASK, 'Task')]

class ActivityStatus:
    PLANNED = 'Planned'
    COMPLETED = 'Completed'
    CANCELLED = 'Cancelled'
    CHOICES = [(PLANNED, 'Planned'), (COMPLETED, 'Completed'), (CANCELLED, 'Cancelled')]

class Activity(db.Model):
    __tablename__ = 'activities'

    id = db.Column(db.Integer, primary_key=True)
    activity_type = db.Column(db.String(50), nullable=False, default=ActivityType.CALL)
    subject = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    activity_date = db.Column(db.Date, nullable=False, default=date.today)
    status = db.Column(db.String(50), nullable=False, default=ActivityStatus.PLANNED)
    
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=True)
    lead_id = db.Column(db.Integer, db.ForeignKey('leads.id'), nullable=True)
    assigned_to_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    created_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'activity_type': self.activity_type,
            'subject': self.subject,
            'description': self.description,
            'activity_date': self.activity_date.isoformat() if self.activity_date else None,
            'status': self.status,
            'customer_id': self.customer_id,
            'customer_name': self.customer.customer_name if self.customer else None,
            'lead_id': self.lead_id,
            'lead_name': self.lead.lead_name if self.lead else None,
            'assigned_to_id': self.assigned_to_id,
            'assigned_to_name': self.assigned_to.name if self.assigned_to else None,
            'created_date': self.created_date.isoformat() if self.created_date else None
        }

    def __repr__(self):
        return f'<Activity {self.id} - {self.subject}>'

