from datetime import date
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, DateField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Length, Optional
from app.models import ActivityType, ActivityStatus, Customer, Lead, User

class ActivityForm(FlaskForm):
    activity_type = SelectField('Activity Type', choices=ActivityType.CHOICES, default=ActivityType.CALL)
    subject = StringField('Subject', validators=[
        DataRequired(message="Subject is required."),
        Length(min=2, max=150, message="Subject must be between 2 and 150 characters.")
    ])
    activity_date = DateField('Activity Date', validators=[
        DataRequired(message="Activity Date is required.")
    ], default=date.today)
    status = SelectField('Status', choices=ActivityStatus.CHOICES, default=ActivityStatus.COMPLETED)
    customer_id = SelectField('Related Customer', coerce=int, validators=[Optional()])
    lead_id = SelectField('Related Lead', coerce=int, validators=[Optional()])
    assigned_to_id = SelectField('Assigned To', coerce=int, validators=[Optional()])
    description = TextAreaField('Description / Notes', validators=[Optional()])
    submit = SubmitField('Save Activity')

    def __init__(self, *args, **kwargs):
        super(ActivityForm, self).__init__(*args, **kwargs)
        customers = Customer.query.order_by(Customer.customer_name).all()
        self.customer_id.choices = [(0, '-- None --')] + [(c.id, f"{c.customer_name} ({c.company_name})") for c in customers]

        leads = Lead.query.order_by(Lead.lead_name).all()
        self.lead_id.choices = [(0, '-- None --')] + [(l.id, f"{l.lead_name} ({l.company_name})") for l in leads]

        users = User.query.filter(User.is_active == True).order_by(User.name).all()
        self.assigned_to_id.choices = [(0, '-- Unassigned --')] + [(u.id, f"{u.name} ({u.role})") for u in users]

