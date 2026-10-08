import json
from flask import request
from flask_login import current_user
from app.models import db, AuditLog

class AuditService:
    @staticmethod
    def log(action, entity_name, record_id=None, old_value=None, new_value=None, details=None, result='Success', user_id=None, user_email=None):
        try:
            ip_address = None
            if request:
                ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
            
            # Identify user
            if user_id is None:
                if current_user and current_user.is_authenticated:
                    user_id = current_user.id
                    user_email = current_user.email
                elif user_email is None and request and 'email' in request.form:
                    user_email = request.form.get('email')

            # Convert dicts/objects to JSON string if needed
            old_str = json.dumps(old_value, default=str) if isinstance(old_value, dict) else (str(old_value) if old_value is not None else None)
            new_str = json.dumps(new_value, default=str) if isinstance(new_value, dict) else (str(new_value) if new_value is not None else None)
            
            # Security: Mask any passwords if they accidentally exist in details/payloads
            if old_str and 'password' in old_str.lower():
                old_str = '[REDACTED_SECURITY_DATA]'
            if new_str and 'password' in new_str.lower():
                new_str = '[REDACTED_SECURITY_DATA]'

            log_entry = AuditLog(
                user_id=user_id,
                user_email=user_email,
                action=action,
                entity_name=entity_name,
                record_id=str(record_id) if record_id is not None else None,
                old_value=old_str,
                new_value=new_str,
                details=details,
                result=result,
                ip_address=ip_address
            )
            db.session.add(log_entry)
            db.session.commit()
            return log_entry
        except Exception as e:
            db.session.rollback()
            # Silently handle audit failure to avoid blocking core transactions, but log to stderr
            print(f"Failed to record audit log: {e}")
            return None

