from datetime import date
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from sqlalchemy import or_
from app.models import db, Activity, ActivityType, ActivityStatus, AuditAction, User
from app.forms import ActivityForm
from app.services.crm_service import CRMService
from app.services.audit_service import AuditService

activity_bp = Blueprint('activities', __name__, url_prefix='/activities')

@activity_bp.route('/')
@login_required
def list_activities():
    page = request.args.get('page', 1, type=int)
    activity_type = request.args.get('type', '').strip()
    status = request.args.get('status', '').strip()
    assigned_to_id = request.args.get('assigned_to_id', 0, type=int)
    date_val = request.args.get('date', '').strip()

    query = CRMService.get_scoped_activities(current_user)

    if activity_type:
        query = query.filter(Activity.activity_type == activity_type)

    if status:
        query = query.filter(Activity.status == status)

    if assigned_to_id > 0:
        query = query.filter(Activity.assigned_to_id == assigned_to_id)

    if date_val:
        try:
            d = date.fromisoformat(date_val)
            query = query.filter(Activity.activity_date == d)
        except ValueError:
            pass

    activities_page = query.order_by(Activity.activity_date.desc(), Activity.id.desc()).paginate(page=page, per_page=10, error_out=False)
    sales_users = User.query.filter(User.is_active == True).order_by(User.name).all()

    return render_template(
        'activities/index.html',
        activities_page=activities_page,
        activity_type=activity_type,
        status=status,
        assigned_to_id=assigned_to_id,
        date_val=date_val,
        sales_users=sales_users,
        types=ActivityType.CHOICES,
        statuses=ActivityStatus.CHOICES
    )

@activity_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    form = ActivityForm()

    if request.method == 'GET':
        cust_id = request.args.get('customer_id', type=int)
        lead_id = request.args.get('lead_id', type=int)
        if cust_id: form.customer_id.data = cust_id
        if lead_id: form.lead_id.data = lead_id

    if form.validate_on_submit():
        activity = Activity(
            activity_type=form.activity_type.data,
            subject=form.subject.data.strip(),
            activity_date=form.activity_date.data,
            status=form.status.data,
            description=form.description.data.strip() if form.description.data else None,
            customer_id=form.customer_id.data if form.customer_id.data > 0 else None,
            lead_id=form.lead_id.data if form.lead_id.data > 0 else None,
            assigned_to_id=form.assigned_to_id.data if form.assigned_to_id.data > 0 else (current_user.id if current_user.is_sales_executive else None)
        )
        db.session.add(activity)
        db.session.commit()

        AuditService.log(
            action=AuditAction.CREATE,
            entity_name='Activity',
            record_id=activity.id,
            new_value=activity.to_dict(),
            details=f"Logged activity: {activity.activity_type} - {activity.subject}",
            user_id=current_user.id
        )

        flash(f"Activity '{activity.subject}' logged successfully.", "success")
        return redirect(url_for('activities.list_activities'))

    return render_template('activities/form.html', form=form, title='Log Activity')

@activity_bp.route('/<int:activity_id>/delete', methods=['POST'])
@login_required
def delete(activity_id):
    activity = Activity.query.get_or_404(activity_id)

    if current_user.is_sales_executive and activity.assigned_to_id != current_user.id:
        flash("You are not authorized to delete this activity.", "danger")
        abort(403)

    old_val = activity.to_dict()
    db.session.delete(activity)
    db.session.commit()

    AuditService.log(
        action=AuditAction.DELETE,
        entity_name='Activity',
        record_id=activity_id,
        old_value=old_val,
        details=f"Deleted activity {old_val.get('subject')}",
        user_id=current_user.id
    )

    flash("Activity removed.", "info")
    return redirect(request.referrer or url_for('activities.list_activities'))

