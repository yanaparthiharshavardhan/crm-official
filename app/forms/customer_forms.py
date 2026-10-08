import re
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Email, Length, Optional, ValidationError
from app.models import Customer, User

class CustomerForm(FlaskForm):
    customer_name = StringField('Customer Name', validators=[
        DataRequired(message="Customer Name is required."),
        Length(min=2, max=100, message="Name must be between 2 and 100 characters.")
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
    address = StringField('Street Address', validators=[
        Optional(),
        Length(max=255, message="Address cannot exceed 255 characters.")
    ])
    city = StringField('City', validators=[
        Optional(),
        Length(max=50, message="City cannot exceed 50 characters.")
    ])
    state = StringField('State / Province', validators=[
        Optional(),
        Length(max=50, message="State cannot exceed 50 characters.")
    ])
    status = SelectField('Status', choices=[('Active', 'Active'), ('Inactive', 'Inactive')], default='Active')
    owner_id = SelectField('Assigned Sales Executive', coerce=int, validators=[Optional()])
    notes = TextAreaField('Notes', validators=[Optional()])
    submit = SubmitField('Save Customer')

    def __init__(self, original_id=None, *args, **kwargs):
        super(CustomerForm, self).__init__(*args, **kwargs)
        self.original_id = original_id
        # Populate sales executives & managers
        users = User.query.filter(User.is_active == True).order_by(User.name).all()
        self.owner_id.choices = [(0, '-- Unassigned --')] + [(u.id, f"{u.name} ({u.role})") for u in users]

    def validate_phone(self, field):
        cleaned = re.sub(r'[\s\-\(\)\+]', '', field.data)
        if not cleaned.isdigit() or len(cleaned) < 10 or len(cleaned) > 15:
            raise ValidationError("Enter a valid phone number (10 to 15 digits).")

    def validate_email(self, field):
        query = Customer.query.filter(Customer.email == field.data.strip().lower())
        if self.original_id:
            query = query.filter(Customer.id != self.original_id)
        if query.first():
            raise ValidationError("A customer with this email address already exists.")

    def validate_phone_unique(self):
        cleaned = self.phone.data.strip()
        query = Customer.query.filter(Customer.phone == cleaned)
        if self.original_id:
            query = query.filter(Customer.id != self.original_id)
        if query.first():
            self.phone.errors.append("A customer with this phone number already exists.")
            return False
        return True

