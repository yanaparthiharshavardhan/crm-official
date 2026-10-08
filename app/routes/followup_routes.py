from datetime import date
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from sqlalchemy import or_
from app.models import (
    db, FollowUp, FollowUpStatus, FollowUpType, AuditAction, Customer, Lead, Opportunity, User
)
from app.forms import FollowUpForm, RescheduleFollowUpForm
from app.services.crm_service import CRMService
from app.services.audit_service import AuditService

followup_bp = Blueprint('followups', __name__, url_prefix='/followups')

@followup_bp.route('/')
@login_required
def list_followups():
    page = request.args.get('page', 1, type=int)
    tab = request.args.get('tab', 'all') # all, upcoming, overdue, completed
    followup_type = request.args.get('type', '').strip()
    status = request.args.get('status', '').strip()
    assigned_to_id = request.args.get('assigned_to_id', 0, type=int)

    query = CRMService.get_scoped_followups(current_user)

    today = date.today()

    if tab == 'upcoming':
        query = query.filter(FollowUp.status == FollowUpStatus.PLANNED, FollowUp.followup_date >= today)
    elif tab == 'overdue':
        query = query.filter(FollowUp.status == FollowUpStatus.PLANNED, FollowUp.followup_date < today)
    elif tab == 'completed':
        query = query.filter(FollowUp.status == FollowUpStatus.COMPLETED)

    if followup_type:
        query = query.filter(FollowUp.followup_type == followup_type)

    if status and tab == 'all':
        query = query.filter(FollowUp.status == status)

    if assigned_to_id > 0:
        query = query.filter(FollowUp.assigned_to_id == assigned_to_id)

    followups_page = query.order_by(FollowUp.followup_date.asc()).paginate(page=page, per_page=10, error_out=False)
    sales_users = User.query.filter(User.is_active == True).order_by(User.name).all()

    # Calculate counts for badge indicators
    base_scoped = CRMService.get_scoped_followups(current_user)
    upcoming_count = base_scoped.filter(FollowUp.status == FollowUpStatus.PLANNED, FollowUp.followup_date >= today).count()
    overdue_count = base_scoped.filter(FollowUp.status == FollowUpStatus.PLANNED, FollowUp.followup_date < today).count()
    completed_count = base_scoped.filter(FollowUp.status == FollowUpStatus.COMPLETED).count()

    reschedule_form = RescheduleFollowUpForm()

    return render_template(
        'followups/index.html',
        followups_page=followups_page,
        tab=tab,
        followup_type=followup_type,
        status=status,
        assigned_to_id=assigned_to_id,
        sales_users=sales_users,
        types=FollowUpType.CHOICES,
        statuses=FollowUpStatus.CHOICES,
        upcoming_count=upcoming_count,
        overdue_count=overdue_count,
        completed_count=completed_count,
        reschedule_form=reschedule_form,
        today=today
    )

@followup_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    form = FollowUpForm()

    # Pre-select customer, lead, or opportunity if provided in query params
    if request.method == 'GET':
        cust_id = request.args.get('customer_id', type=int)
        lead_id = request.args.get('lead_id', type=int)
        opp_id = request.args.get('opportunity_id', type=int)
        if cust_id: form.customer_id.data = cust_id
        if lead_id: form.lead_id.data = lead_id
        if opp_id: form.opportunity_id.data = opp_id

    if form.validate_on_submit():
        # Server-side date validation
        is_valid, err_msg = CRMService.validate_followup_date(form.followup_date.data, form.status.data)
        if not is_valid:
            flash(err_msg, 'danger')
            return render_template('followups/form.html', form=form, title='Schedule Follow-Up')

        fu = FollowUp(
            subject=form.subject.data.strip(),
            followup_type=form.followup_type.data,
            followup_date=form.followup_date.data,
            status=form.status.data,
            remarks=form.remarks.data.strip() if form.remarks.data else None,
            customer_id=form.customer_id.data if form.customer_id.data > 0 else None,
            lead_id=form.lead_id.data if form.lead_id.data > 0 else None,
            opportunity_id=form.opportunity_id.data if form.opportunity_id.data > 0 else None,
            assigned_to_id=form.assigned_to_id.data if form.assigned_to_id.data > 0 else (current_user.id if current_user.is_sales_executive else None)
        )
        db.session.add(fu)
        db.session.commit()

        AuditService.log(
            action=AuditAction.CREATE,
            entity_name='FollowUp',
            record_id=fu.id,
            new_value=fu.to_dict(),
            details=f"Scheduled follow-up '{fu.subject}' for {fu.followup_date}",
            user_id=current_user.id
        )

        flash(f"Follow-up '{fu.subject}' scheduled successfully.", "success")
        return redirect(url_for('followups.list_followups'))

    return render_template('followups/form.html', form=form, title='Schedule Follow-Up')

@followup_bp.route('/<int:followup_id>/complete', methods=['POST'])
@login_required
def complete(followup_id):
    fu = FollowUp.query.get_or_404(followup_id)

    if current_user.is_sales_executive and fu.assigned_to_id != current_user.id:
        flash("You are not authorized to complete this follow-up.", "danger")
        abort(403)

    old_status = fu.status
    fu.status = FollowUpStatus.COMPLETED
    completion_notes = request.form.get('completion_notes', '').strip()
    if completion_notes:
        fu.remarks = (fu.remarks or '') + f"\n[Completed on {date.today()}]: {completion_notes}"

    db.session.commit()

    AuditService.log(
        action=AuditAction.UPDATE,
        entity_name='FollowUp',
        record_id=fu.id,
        old_value={'status': old_status},
        new_value={'status': FollowUpStatus.COMPLETED},
        details=f"Marked follow-up '{fu.subject}' as Completed",
        user_id=current_user.id
    )

    flash("Follow-up marked as Completed.", "success")
    return redirect(request.referrer or url_for('followups.list_followups'))

@followup_bp.route('/<int:followup_id>/reschedule', methods=['POST'])
@login_required
def reschedule(followup_id):
    fu = FollowUp.query.get_or_404(followup_id)

    if current_user.is_sales_executive and fu.assigned_to_id != current_user.id:
        flash("You are not authorized to reschedule this follow-up.", "danger")
        abort(403)

    form = RescheduleFollowUpForm()
    if form.validate_on_submit():
        new_date = form.new_followup_date.data
        if new_date < date.today():
            flash("Follow-up date cannot be earlier than today.", "danger")
            return redirect(request.referrer or url_for('followups.list_followups'))

        old_date = fu.followup_date
        fu.followup_date = new_date
        fu.status = FollowUpStatus.PLANNED
        reason = form.remarks.data.strip()
        fu.remarks = (fu.remarks or '') + f"\n[Rescheduled from {old_date} to {new_date}]: {reason}"

        db.session.commit()

        AuditService.log(
            action=AuditAction.UPDATE,
            entity_name='FollowUp',
            record_id=fu.id,
            old_value={'followup_date': str(old_date)},
            new_value={'followup_date': str(new_date), 'remarks': reason},
            details=f"Rescheduled follow-up '{fu.subject}' from {old_date} to {new_date}",
            user_id=current_user.id
        )

        flash(f"Follow-up rescheduled to {new_date}.", "success")
    else:
        for err in form.errors.values():
            flash(err[0], "danger")

    return redirect(request.referrer or url_for('followups.list_followups'))

@followup_bp.route('/<int:followup_id>/cancel', methods=['POST'])
@login_required
def cancel(followup_id):
    fu = FollowUp.query.get_or_404(followup_id)

    if current_user.is_sales_executive and fu.assigned_to_id != current_user.id:
        flash("You are not authorized to cancel this follow-up.", "danger")
        abort(403)

    old_status = fu.status
    fu.status = FollowUpStatus.CANCELLED
    db.session.commit()

    AuditService.log(
        action=AuditAction.UPDATE,
        entity_name='FollowUp',
        record_id=fu.id,
        old_value={'status': old_status},
        new_value={'status': FollowUpStatus.CANCELLED},
        details=f"Cancelled follow-up '{fu.subject}'",
        user_id=current_user.id
    )

    flash("Follow-up cancelled.", "info")
    return redirect(request.referrer or url_for('followups.list_followups'))

