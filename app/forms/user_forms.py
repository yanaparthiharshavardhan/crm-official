import re
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, Length, Optional, ValidationError
from app.models import Role, User

class UserCreateForm(FlaskForm):
    name = StringField('Full Name', validators=[
        DataRequired(message="Name is required."),
        Length(min=2, max=100, message="Name must be between 2 and 100 characters.")
    ])
    email = StringField('Email Address', validators=[
        DataRequired(message="Email is required."),
        Email(message="Enter a valid email address."),
        Length(max=120)
    ])
    role = SelectField('User Role', choices=Role.CHOICES, default=Role.SALES_EXECUTIVE)
    password = PasswordField('Initial Password', validators=[
        DataRequired(message="Password is required."),
        Length(min=8, message="Password must be at least 8 characters long.")
    ])
    is_active = BooleanField('Active Account', default=True)
    submit = SubmitField('Create User')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data.strip().lower()).first():
            raise ValidationError("A user with this email address already exists.")

    def validate_password(self, field):
        p = field.data
        if not re.search(r'[A-Z]', p):
            raise ValidationError("Password must contain at least one uppercase letter.")
        if not re.search(r'[a-z]', p):
            raise ValidationError("Password must contain at least one lowercase letter.")
        if not re.search(r'[0-9]', p):
            raise ValidationError("Password must contain at least one number.")
        if not re.search(r'[\W_]', p):
            raise ValidationError("Password must contain at least one special character.")

class UserEditForm(FlaskForm):
    name = StringField('Full Name', validators=[
        DataRequired(message="Name is required."),
        Length(min=2, max=100)
    ])
    email = StringField('Email Address', validators=[
        DataRequired(message="Email is required."),
        Email(message="Enter a valid email address."),
        Length(max=120)
    ])
    role = SelectField('User Role', choices=Role.CHOICES)
    is_active = BooleanField('Active Account')
    submit = SubmitField('Update User')

    def __init__(self, original_id=None, *args, **kwargs):
        super(UserEditForm, self).__init__(*args, **kwargs)
        self.original_id = original_id

    def validate_email(self, field):
        query = User.query.filter_by(email=field.data.strip().lower())
        if self.original_id:
            query = query.filter(User.id != self.original_id)
        if query.first():
            raise ValidationError("A user with this email address already exists.")

class AdminResetPasswordForm(FlaskForm):
    new_password = PasswordField('New Password', validators=[
        DataRequired(message="New password is required."),
        Length(min=8, message="Password must be at least 8 characters long.")
    ])
    submit = SubmitField('Reset Password')

    def validate_new_password(self, field):
        p = field.data
        if not re.search(r'[A-Z]', p):
            raise ValidationError("Password must contain at least one uppercase letter.")
        if not re.search(r'[a-z]', p):
            raise ValidationError("Password must contain at least one lowercase letter.")
        if not re.search(r'[0-9]', p):
            raise ValidationError("Password must contain at least one number.")
        if not re.search(r'[\W_]', p):
            raise ValidationError("Password must contain at least one special character.")

