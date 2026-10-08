from datetime import date
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, DateField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Length, Optional, ValidationError
from app.models import FollowUpStatus, FollowUpType, Customer, Lead, Opportunity, User

class FollowUpForm(FlaskForm):
    subject = StringField('Subject / Purpose', validators=[
        DataRequired(message="Subject is required."),
        Length(min=2, max=150, message="Subject must be between 2 and 150 characters.")
    ])
    followup_type = SelectField('Follow-Up Type', choices=FollowUpType.CHOICES, default=FollowUpType.CALL)
    followup_date = DateField('Follow-Up Date', validators=[
        DataRequired(message="Follow-Up Date is required.")
    ], default=date.today)
    status = SelectField('Status', choices=FollowUpStatus.CHOICES, default=FollowUpStatus.PLANNED)
    
    customer_id = SelectField('Related Customer', coerce=int, validators=[Optional()])
    lead_id = SelectField('Related Lead', coerce=int, validators=[Optional()])
    opportunity_id = SelectField('Related Opportunity', coerce=int, validators=[Optional()])
    assigned_to_id = SelectField('Assigned To', coerce=int, validators=[Optional()])
    remarks = TextAreaField('Remarks / Agenda', validators=[Optional()])
    submit = SubmitField('Schedule Follow-Up')

    def __init__(self, *args, **kwargs):
        super(FollowUpForm, self).__init__(*args, **kwargs)
        customers = Customer.query.order_by(Customer.customer_name).all()
        self.customer_id.choices = [(0, '-- None --')] + [(c.id, f"{c.customer_name} ({c.company_name})") for c in customers]

        leads = Lead.query.order_by(Lead.lead_name).all()
        self.lead_id.choices = [(0, '-- None --')] + [(l.id, f"{l.lead_name} ({l.company_name})") for l in leads]

        opps = Opportunity.query.order_by(Opportunity.opportunity_name).all()
        self.opportunity_id.choices = [(0, '-- None --')] + [(o.id, f"{o.opportunity_name} (${o.amount:,.0f})") for o in opps]

        users = User.query.filter(User.is_active == True).order_by(User.name).all()
        self.assigned_to_id.choices = [(0, '-- Unassigned --')] + [(u.id, f"{u.name} ({u.role})") for u in users]

    def validate_followup_date(self, field):
        if self.status.data == FollowUpStatus.PLANNED and field.data and field.data < date.today():
            raise ValidationError("Follow-up date cannot be earlier than today.")

class RescheduleFollowUpForm(FlaskForm):
    new_followup_date = DateField('New Follow-Up Date', validators=[
        DataRequired(message="New follow-up date is required.")
    ])
    remarks = TextAreaField('Reschedule Reason / Notes', validators=[
        DataRequired(message="Please provide a reason for rescheduling.")
    ])
    submit = SubmitField('Confirm Reschedule')

    def validate_new_followup_date(self, field):
        if field.data and field.data < date.today():
            raise ValidationError("Follow-up date cannot be earlier than today.")

