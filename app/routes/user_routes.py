from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from sqlalchemy import or_
from app.models import db, User, Role, AuditAction
from app.forms import UserCreateForm, UserEditForm, AdminResetPasswordForm
from app.routes.auth_routes import roles_required
from app.services.auth_service import AuthService
from app.services.audit_service import AuditService

user_bp = Blueprint('users', __name__, url_prefix='/users')

@user_bp.route('/')
@login_required
@roles_required(Role.ADMIN)
def list_users():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '').strip()
    role = request.args.get('role', '').strip()
    status = request.args.get('status', '').strip()

    query = User.query

    if search:
        search_fmt = f"%{search}%"
        query = query.filter(or_(User.name.ilike(search_fmt), User.email.ilike(search_fmt)))

    if role:
        query = query.filter(User.role == role)

    if status == 'active':
        query = query.filter(User.is_active == True)
    elif status == 'inactive':
        query = query.filter(User.is_active == False)
    elif status == 'locked':
        query = query.filter(User.lockout_end != None, User.lockout_end > datetime.utcnow())

    users_page = query.order_by(User.name.asc()).paginate(page=page, per_page=10, error_out=False)

    return render_template(
        'users/index.html',
        users_page=users_page,
        search=search,
        role=role,
        status=status,
        roles=Role.CHOICES,
        now=datetime.utcnow()
    )

@user_bp.route('/create', methods=['GET', 'POST'])
@login_required
@roles_required(Role.ADMIN)
def create():
    form = UserCreateForm()
    if form.validate_on_submit():
        user, msg = AuthService.create_user(
            name=form.name.data,
            email=form.email.data,
            password=form.password.data,
            role=form.role.data,
            is_active=form.is_active.data,
            created_by=current_user
        )
        if user:
            flash(f"User {user.name} ({user.email}) created successfully as {user.role}.", "success")
            return redirect(url_for('users.list_users'))
        else:
            flash(msg, "danger")

    return render_template('users/form.html', form=form, title='Create User')

@user_bp.route('/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@roles_required(Role.ADMIN)
def edit(user_id):
    user = User.query.get_or_404(user_id)
    form = UserEditForm(original_id=user.id, obj=user)

    if form.validate_on_submit():
        old_val = {'name': user.name, 'email': user.email, 'role': user.role, 'is_active': user.is_active}
        
        # Check role change
        role_changed = (user.role != form.role.data)
        
        user.name = form.name.data.strip()
        user.email = form.email.data.strip().lower()
        user.role = form.role.data
        user.is_active = form.is_active.data

        db.session.commit()

        if role_changed:
            AuditService.log(
                action=AuditAction.ROLE_CHANGE,
                entity_name='User',
                record_id=user.id,
                old_value={'role': old_val['role']},
                new_value={'role': user.role},
                details=f"Admin {current_user.email} changed role of {user.email} from {old_val['role']} to {user.role}",
                user_id=current_user.id
            )

        AuditService.log(
            action=AuditAction.UPDATE,
            entity_name='User',
            record_id=user.id,
            old_value=old_val,
            new_value={'name': user.name, 'email': user.email, 'role': user.role, 'is_active': user.is_active},
            details=f"Admin updated user {user.email}",
            user_id=current_user.id
        )

        flash(f"User {user.name} updated successfully.", "success")
        return redirect(url_for('users.list_users'))

    return render_template('users/form.html', form=form, title='Edit User', edit_user=user)

@user_bp.route('/<int:user_id>/unlock', methods=['POST'])
@login_required
@roles_required(Role.ADMIN)
def unlock(user_id):
    user = User.query.get_or_404(user_id)
    AuthService.unlock_user(user, current_user)
    flash(f"Account for {user.name} ({user.email}) has been unlocked.", "success")
    return redirect(url_for('users.list_users'))

@user_bp.route('/<int:user_id>/reset-password', methods=['GET', 'POST'])
@login_required
@roles_required(Role.ADMIN)
def reset_password(user_id):
    user = User.query.get_or_404(user_id)
    form = AdminResetPasswordForm()

    if form.validate_on_submit():
        user.set_password(form.new_password.data)
        db.session.commit()

        AuditService.log(
            action=AuditAction.SECURITY,
            entity_name='User',
            record_id=user.id,
            details=f"Admin {current_user.email} reset password for user {user.email}",
            user_id=current_user.id
        )

        flash(f"Password for {user.name} ({user.email}) has been reset.", "success")
        return redirect(url_for('users.list_users'))

    return render_template('users/reset_password.html', form=form, target_user=user)

@user_bp.route('/<int:user_id>/toggle-status', methods=['POST'])
@login_required
@roles_required(Role.ADMIN)
def toggle_status(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("You cannot deactivate your own account.", "warning")
        return redirect(url_for('users.list_users'))

    user.is_active = not user.is_active
    db.session.commit()

    action_text = "Activated" if user.is_active else "Deactivated"
    AuditService.log(
        action=AuditAction.UPDATE,
        entity_name='User',
        record_id=user.id,
        details=f"Admin {current_user.email} {action_text.lower()} account {user.email}",
        user_id=current_user.id
    )

    flash(f"User {user.name} has been {action_text.lower()}.", "info")
    return redirect(url_for('users.list_users'))

