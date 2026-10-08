from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError
import re

class LoginForm(FlaskForm):
    email = StringField('Email Address', validators=[
        DataRequired(message="Email is required."),
        Email(message="Enter a valid email address.")
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message="Password is required.")
    ])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class RegisterForm(FlaskForm):
    name = StringField('Full Name', validators=[
        DataRequired(message="Full Name is required."),
        Length(min=2, max=100, message="Name must be between 2 and 100 characters.")
    ])
    email = StringField('Email Address', validators=[
        DataRequired(message="Email is required."),
        Email(message="Enter a valid email address."),
        Length(max=120, message="Email cannot exceed 120 characters.")
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message="Password is required."),
        Length(min=8, message="Password must be at least 8 characters long.")
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(message="Please confirm your password."),
        EqualTo('password', message="Passwords must match.")
    ])
    submit = SubmitField('Register')

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

class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('Current Password', validators=[
        DataRequired(message="Current password is required.")
    ])
    new_password = PasswordField('New Password', validators=[
        DataRequired(message="New password is required."),
        Length(min=8, message="Password must be at least 8 characters long.")
    ])
    confirm_password = PasswordField('Confirm New Password', validators=[
        DataRequired(message="Please confirm your new password."),
        EqualTo('new_password', message="Passwords must match.")
    ])
    submit = SubmitField('Update Password')

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

