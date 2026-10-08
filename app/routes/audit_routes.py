import csv
import io
from datetime import datetime, date
from flask import Blueprint, render_template, request, Response
from flask_login import login_required, current_user
from sqlalchemy import func
from app.models import AuditLog, AuditAction, User, Role
from app.routes.auth_routes import roles_required

audit_bp = Blueprint('audit', __name__, url_prefix='/audit')

@audit_bp.route('/')
@login_required
@roles_required(Role.ADMIN, Role.MANAGER)
def list_logs():
    page = request.args.get('page', 1, type=int)
    action = request.args.get('action', '').strip()
    entity_name = request.args.get('entity_name', '').strip()
    user_id = request.args.get('user_id', 0, type=int)
    start_date = request.args.get('start_date', '').strip()
    end_date = request.args.get('end_date', '').strip()

    query = AuditLog.query

    if action:
        query = query.filter(AuditLog.action == action)

    if entity_name:
        query = query.filter(AuditLog.entity_name == entity_name)

    if user_id > 0:
        query = query.filter(AuditLog.user_id == user_id)

    if start_date:
        try:
            s_d = datetime.strptime(start_date, '%Y-%m-%d').date()
            query = query.filter(func.date(AuditLog.created_date) >= s_d)
        except ValueError:
            pass

    if end_date:
        try:
            e_d = datetime.strptime(end_date, '%Y-%m-%d').date()
            query = query.filter(func.date(AuditLog.created_date) <= e_d)
        except ValueError:
            pass

    if request.args.get('export') == 'csv':
        all_logs = query.order_by(AuditLog.created_date.desc()).all()
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['ID', 'Timestamp', 'User', 'Action', 'Module/Entity', 'Record ID', 'Result', 'IP Address', 'Details', 'Old Value', 'New Value'])
        for log in all_logs:
            writer.writerow([
                log.id,
                log.created_date.strftime('%Y-%m-%d %H:%M:%S') if log.created_date else '',
                log.user.email if log.user else (log.user_email or 'System'),
                log.action,
                log.entity_name,
                log.record_id or '',
                log.result,
                log.ip_address or '',
                log.details or '',
                log.old_value or '',
                log.new_value or ''
            ])
        return Response(output.getvalue(), mimetype='text/csv', headers={"Content-Disposition": "attachment;filename=audit_logs.csv"})

    logs_page = query.order_by(AuditLog.created_date.desc()).paginate(page=page, per_page=15, error_out=False)
    users = User.query.order_by(User.name).all()
    entities = ['Auth', 'User', 'Customer', 'Lead', 'Opportunity', 'FollowUp', 'Activity', 'Authorization']

    return render_template(
        'audit/index.html',
        logs_page=logs_page,
        action=action,
        entity_name=entity_name,
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
        actions=AuditAction.ALL,
        entities=entities,
        users=users
    )

