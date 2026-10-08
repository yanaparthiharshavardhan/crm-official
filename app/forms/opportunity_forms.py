from datetime import date
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, FloatField, IntegerField, DateField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Length, Optional, NumberRange, ValidationError
from app.models import OpportunityStage, OpportunityStatus, Customer, User

class OpportunityForm(FlaskForm):
    opportunity_name = StringField('Opportunity Name', validators=[
        DataRequired(message="Opportunity Name is required."),
        Length(min=2, max=150, message="Opportunity name must be between 2 and 150 characters.")
    ])
    customer_id = SelectField('Customer', coerce=int, validators=[
        DataRequired(message="Customer is required.")
    ])
    amount = FloatField('Opportunity Amount ($)', validators=[
        DataRequired(message="Opportunity Amount is required."),
        NumberRange(min=0.01, message="Opportunity Amount must be greater than 0.")
    ])
    stage = SelectField('Stage', choices=OpportunityStage.CHOICES, default=OpportunityStage.QUALIFICATION)
    probability = IntegerField('Probability (%)', validators=[
        DataRequired(message="Probability is required."),
        NumberRange(min=0, max=100, message="Probability must be between 0 and 100.")
    ], default=20)
    expected_close_date = DateField('Expected Close Date', validators=[
        DataRequired(message="Expected Close Date is required.")
    ], default=date.today)
    source = StringField('Lead / Opportunity Source', validators=[
        Optional(),
        Length(max=50)
    ])
    assigned_to_id = SelectField('Assigned Sales Executive', coerce=int, validators=[Optional()])
    notes = TextAreaField('Notes', validators=[Optional()])
    submit = SubmitField('Save Opportunity')

    def __init__(self, user=None, *args, **kwargs):
        super(OpportunityForm, self).__init__(*args, **kwargs)
        # Populate customers
        customers = Customer.query.order_by(Customer.customer_name).all()
        self.customer_id.choices = [(c.id, f"{c.customer_name} ({c.company_name})") for c in customers]
        
        # Populate users
        users = User.query.filter(User.is_active == True).order_by(User.name).all()
        self.assigned_to_id.choices = [(0, '-- Unassigned --')] + [(u.id, f"{u.name} ({u.role})") for u in users]

    def validate_amount(self, field):
        if field.data is None or field.data <= 0:
            raise ValidationError("Opportunity Amount must be greater than 0.")

    def validate_probability(self, field):
        if field.data is None or field.data < 0 or field.data > 100:
            raise ValidationError("Probability must be between 0 and 100.")

    def validate_expected_close_date(self, field):
        if self.stage.data not in [OpportunityStage.WON, OpportunityStage.LOST]:
            if field.data and field.data < date.today():
                raise ValidationError("Expected Close Date cannot be in the past.")

