from datetime import datetime
from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_user, logout_user, login_required, current_user
from app.models import db, User, Role, AuditAction
from app.forms import LoginForm, RegisterForm, ChangePasswordForm
from app.services.auth_service import AuthService
from app.services.audit_service import AuditService

auth_bp = Blueprint('auth', __name__)

def roles_required(*roles):
    """Decorator to enforce role-based access control."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login', next=request.url))
            if current_user.role not in roles:
                AuditService.log(
                    action='Unauthorized Access Attempt',
                    entity_name='Authorization',
                    details=f"User {current_user.email} ({current_user.role}) attempted to access restricted endpoint: {request.path}",
                    result='Failure'
                )
                flash("Access denied. You do not have permission to view this resource.", "danger")
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        password = form.password.data
        remember = form.remember_me.data
        
        user = User.query.filter_by(email=email).first()
        
        if user:
            if not user.is_active:
                AuditService.log(
                    action=AuditAction.FAILED_LOGIN,
                    entity_name='Auth',
                    record_id=user.id,
                    details=f"Deactivated user {email} attempted to log in.",
                    result='Failure',
                    user_id=user.id
                )
                flash("This account has been deactivated. Please contact your Administrator.", "danger")
                return render_template('auth/login.html', form=form)

            if user.is_locked_out:
                minutes_left = int((user.lockout_end - datetime.utcnow()).total_seconds() // 60) + 1
                flash(f"Account is locked due to too many failed attempts. Try again in {minutes_left} minute(s) or contact Administrator.", "danger")
                return render_template('auth/login.html', form=form)

            if user.check_password(password):
                login_user(user, remember=remember)
                AuthService.handle_successful_login(user)
                flash(f"Welcome back, {user.name}!", "success")
                next_page = request.args.get('next')
                return redirect(next_page or url_for('dashboard.index'))
            else:
                locked, msg = AuthService.handle_failed_login(user, email)
                flash(msg, "danger")
        else:
            AuthService.handle_failed_login(None, email)
            flash("Invalid email or password.", "danger")
            
    return render_template('auth/login.html', form=form)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    form = RegisterForm()
    if form.validate_on_submit():
        user, msg = AuthService.create_user(
            name=form.name.data,
            email=form.email.data,
            password=form.password.data,
            role=Role.SALES_EXECUTIVE
        )
        if user:
            flash("Registration successful! You may now sign in.", "success")
            return redirect(url_for('auth.login'))
        else:
            flash(msg, "danger")
            
    return render_template('auth/register.html', form=form)

@auth_bp.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    user_id = current_user.id
    user_email = current_user.email
    logout_user()
    AuditService.log(
        action=AuditAction.LOGOUT,
        entity_name='Auth',
        record_id=user_id,
        details=f"User {user_email} logged out.",
        result='Success',
        user_id=user_id,
        user_email=user_email
    )
    flash("You have been signed out successfully.", "info")
    return redirect(url_for('auth.login'))

@auth_bp.route('/profile/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            flash("Current password is incorrect.", "danger")
            return render_template('auth/change_password.html', form=form)
            
        current_user.set_password(form.new_password.data)
        db.session.commit()
        AuditService.log(
            action=AuditAction.SECURITY,
            entity_name='User',
            record_id=current_user.id,
            details=f"User {current_user.email} changed their password.",
            result='Success',
            user_id=current_user.id
        )
        flash("Your password has been changed successfully.", "success")
        return redirect(url_for('dashboard.index'))
        
    return render_template('auth/change_password.html', form=form)
