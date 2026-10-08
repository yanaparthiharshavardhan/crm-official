import re
from datetime import date
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, FloatField, TextAreaField, DateField, SubmitField
from wtforms.validators import DataRequired, Email, Length, Optional, NumberRange, ValidationError
from app.models import Lead, LeadStatus, LeadPriority, LeadSource, User

class LeadForm(FlaskForm):
    lead_name = StringField('Lead Name', validators=[
        DataRequired(message="Lead name is required."),
        Length(min=2, max=100, message="Lead name must be between 2 and 100 characters.")
    ])
    email = StringField('Email Address', validators=[
        DataRequired(message="Email is required."),
        Email(message="Enter a valid email address."),
        Length(max=120, message="Email cannot exceed 120 characters.")
    ])
    phone = StringField('Phone Number', validators=[
        DataRequired(message="Phone number is required."),
        Length(min=10, max=15, message="Phone number must be between 10 and 15 digits.")
    ])
    company_name = StringField('Company Name', validators=[
        DataRequired(message="Company Name is required."),
        Length(max=100, message="Company name cannot exceed 100 characters.")
    ])
    source = SelectField('Lead Source', choices=LeadSource.CHOICES, default=LeadSource.WEBSITE)
    status = SelectField('Lead Status', choices=LeadStatus.CHOICES, default=LeadStatus.NEW)
    priority = SelectField('Priority', choices=LeadPriority.CHOICES, default=LeadPriority.MEDIUM)
    expected_value = FloatField('Expected Value ($)', validators=[
        Optional(),
        NumberRange(min=0, message="Expected value must be a positive number.")
    ], default=0.0)
    assigned_to_id = SelectField('Assigned Sales Executive', coerce=int, validators=[Optional()])
    notes = TextAreaField('Notes', validators=[Optional()])
    submit = SubmitField('Save Lead')

    def __init__(self, original_id=None, *args, **kwargs):
        super(LeadForm, self).__init__(*args, **kwargs)
        self.original_id = original_id
        users = User.query.filter(User.is_active == True).order_by(User.name).all()
        self.assigned_to_id.choices = [(0, '-- Unassigned --')] + [(u.id, f"{u.name} ({u.role})") for u in users]

    def validate_phone(self, field):
        cleaned = re.sub(r'[\s\-\(\)\+]', '', field.data)
        if not cleaned.isdigit() or len(cleaned) < 10 or len(cleaned) > 15:
            raise ValidationError("Enter a valid phone number (10 to 15 digits).")

class ConvertLeadForm(FlaskForm):
    opportunity_name = StringField('Opportunity Name', validators=[
        Optional(),
        Length(max=150, message="Opportunity name cannot exceed 150 characters.")
    ])
    amount = FloatField('Deal Amount ($)', validators=[
        Optional(),
        NumberRange(min=0.01, message="Opportunity Amount must be greater than 0.")
    ])
    expected_close_date = DateField('Expected Close Date', validators=[Optional()], default=date.today)
    submit = SubmitField('Confirm Conversion')

    def validate_expected_close_date(self, field):
        if field.data and field.data < date.today():
            raise ValidationError("Expected Close Date cannot be in the past.")

