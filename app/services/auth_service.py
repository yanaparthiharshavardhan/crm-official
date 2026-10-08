import re
from datetime import datetime, timedelta
from app.models import db, User, Role, AuditAction
from app.services.audit_service import AuditService

class AuthService:
    @staticmethod
    def validate_password_strength(password):
        """
        Validates password policy:
        - At least 8 characters
        - At least one uppercase letter
        - At least one lowercase letter
        - At least one number
        - At least one special character
        """
        if not password or len(password) < 8:
            return False, "Password must be at least 8 characters long."
        if not re.search(r'[A-Z]', password):
            return False, "Password must contain at least one uppercase letter."
        if not re.search(r'[a-z]', password):
            return False, "Password must contain at least one lowercase letter."
        if not re.search(r'[0-9]', password):
            return False, "Password must contain at least one number."
        if not re.search(r'[\W_]', password):
            return False, "Password must contain at least one special character."
        return True, "Password meets complexity requirements."

    @staticmethod
    def handle_failed_login(user, email_attempted):
        """Increments failed login attempts and triggers lockout if threshold reached."""
        if user:
            user.failed_login_count += 1
            if user.failed_login_count >= 5:
                user.lockout_end = datetime.utcnow() + timedelta(minutes=15)
                db.session.commit()
                AuditService.log(
                    action=AuditAction.LOCKOUT,
                    entity_name='Auth',
                    record_id=user.id,
                    details=f"Account locked out for 15 minutes due to {user.failed_login_count} consecutive failed login attempts.",
                    result='Failure',
                    user_id=user.id,
                    user_email=user.email
                )
                return True, "Account is locked due to too many failed attempts. Try again in 15 minutes or contact Administrator."
            db.session.commit()
            remaining = 5 - user.failed_login_count
            AuditService.log(
                action=AuditAction.FAILED_LOGIN,
                entity_name='Auth',
                record_id=user.id,
                details=f"Invalid password for {user.email}. Attempt {user.failed_login_count}/5.",
                result='Failure',
                user_id=user.id,
                user_email=user.email
            )
            return False, f"Invalid email or password. {remaining} attempt(s) remaining before account lockout."
        else:
            AuditService.log(
                action=AuditAction.FAILED_LOGIN,
                entity_name='Auth',
                details=f"Login attempt with non-existent email: {email_attempted}",
                result='Failure',
                user_email=email_attempted
            )
            return False, "Invalid email or password."

    @staticmethod
    def handle_successful_login(user):
        """Resets failed attempts and logs successful login."""
        user.failed_login_count = 0
        user.lockout_end = None
        db.session.commit()
        AuditService.log(
            action=AuditAction.LOGIN,
            entity_name='Auth',
            record_id=user.id,
            details=f"User {user.email} logged in successfully.",
            result='Success',
            user_id=user.id,
            user_email=user.email
        )

    @staticmethod
    def unlock_user(user, admin_user):
        """Unlocks a locked user account."""
        user.failed_login_count = 0
        user.lockout_end = None
        db.session.commit()
        AuditService.log(
            action=AuditAction.UNLOCK,
            entity_name='User',
            record_id=user.id,
            details=f"Account unlocked by Administrator {admin_user.email}.",
            result='Success',
            user_id=admin_user.id
        )

    @staticmethod
    def create_user(name, email, password, role=Role.SALES_EXECUTIVE, is_active=True, created_by=None):
        is_valid, msg = AuthService.validate_password_strength(password)
        if not is_valid:
            return None, msg

        existing = User.query.filter_by(email=email.strip().lower()).first()
        if existing:
            return None, "Email address is already registered."

        user = User(
            name=name.strip(),
            email=email.strip().lower(),
            role=role,
            is_active=is_active
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        AuditService.log(
            action=AuditAction.CREATE,
            entity_name='User',
            record_id=user.id,
            new_value={'name': user.name, 'email': user.email, 'role': user.role},
            details=f"User {user.email} created with role {user.role}.",
            user_id=created_by.id if created_by else None
        )
        return user, "User created successfully."

