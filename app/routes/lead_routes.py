from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from sqlalchemy import or_
from app.models import db, Lead, LeadStatus, LeadPriority, LeadSource, AuditAction, User
from app.forms import LeadForm, ConvertLeadForm
from app.services.crm_service import CRMService
from app.services.audit_service import AuditService

lead_bp = Blueprint('leads', __name__, url_prefix='/leads')

@lead_bp.route('/')
@login_required
def list_leads():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '').strip()
    status = request.args.get('status', '').strip()
    priority = request.args.get('priority', '').strip()
    source = request.args.get('source', '').strip()
    assigned_to_id = request.args.get('assigned_to_id', 0, type=int)

    query = CRMService.get_scoped_leads(current_user)

    if search:
        search_fmt = f"%{search}%"
        query = query.filter(
            or_(
                Lead.lead_name.ilike(search_fmt),
                Lead.company_name.ilike(search_fmt),
                Lead.email.ilike(search_fmt),
                Lead.phone.ilike(search_fmt),
                Lead.lead_code.ilike(search_fmt)
            )
        )

    if status:
        query = query.filter(Lead.status == status)

    if priority:
        query = query.filter(Lead.priority == priority)

    if source:
        query = query.filter(Lead.source == source)

    if assigned_to_id > 0:
        query = query.filter(Lead.assigned_to_id == assigned_to_id)

    leads_page = query.order_by(Lead.created_date.desc()).paginate(page=page, per_page=10, error_out=False)
    sales_users = User.query.filter(User.is_active == True).order_by(User.name).all()

    return render_template(
        'leads/index.html',
        leads_page=leads_page,
        search=search,
        status=status,
        priority=priority,
        source=source,
        assigned_to_id=assigned_to_id,
        sales_users=sales_users,
        statuses=LeadStatus.ALL,
        sources=LeadSource.CHOICES,
        priorities=LeadPriority.CHOICES
    )

@lead_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    form = LeadForm()
    if form.validate_on_submit():
        lead = Lead(
            lead_code=CRMService.generate_lead_code(),
            lead_name=form.lead_name.data.strip(),
            email=form.email.data.strip().lower(),
            phone=form.phone.data.strip(),
            company_name=form.company_name.data.strip(),
            source=form.source.data,
            status=form.status.data,
            priority=form.priority.data,
            expected_value=form.expected_value.data or 0.0,
            notes=form.notes.data.strip() if form.notes.data else None,
            assigned_to_id=form.assigned_to_id.data if form.assigned_to_id.data > 0 else (current_user.id if current_user.is_sales_executive else None)
        )
        db.session.add(lead)
        db.session.commit()

        AuditService.log(
            action=AuditAction.CREATE,
            entity_name='Lead',
            record_id=lead.id,
            new_value=lead.to_dict(),
            details=f"Created lead {lead.lead_code} ({lead.lead_name})",
            user_id=current_user.id
        )

        flash(f"Lead {lead.lead_name} ({lead.lead_code}) created successfully.", 'success')
        return redirect(url_for('leads.details', lead_id=lead.id))

    return render_template('leads/form.html', form=form, title='Create Lead')

@lead_bp.route('/<int:lead_id>')
@login_required
def details(lead_id):
    lead = Lead.query.get_or_404(lead_id)

    if current_user.is_sales_executive and lead.assigned_to_id != current_user.id:
        flash("You are not authorized to view this lead.", "danger")
        abort(403)

    convert_form = ConvertLeadForm()
    return render_template('leads/details.html', lead=lead, convert_form=convert_form)

@lead_bp.route('/<int:lead_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(lead_id):
    lead = Lead.query.get_or_404(lead_id)

    if current_user.is_sales_executive and lead.assigned_to_id != current_user.id:
        flash("You are not authorized to edit this lead.", "danger")
        abort(403)

    form = LeadForm(original_id=lead.id, obj=lead)
    if form.validate_on_submit():
        old_val = lead.to_dict()

        lead.lead_name = form.lead_name.data.strip()
        lead.email = form.email.data.strip().lower()
        lead.phone = form.phone.data.strip()
        lead.company_name = form.company_name.data.strip()
        lead.source = form.source.data
        lead.status = form.status.data
        lead.priority = form.priority.data
        lead.expected_value = form.expected_value.data or 0.0
        lead.notes = form.notes.data.strip() if form.notes.data else None
        
        if not current_user.is_sales_executive or current_user.is_admin or current_user.is_manager:
            lead.assigned_to_id = form.assigned_to_id.data if form.assigned_to_id.data > 0 else None

        db.session.commit()

        AuditService.log(
            action=AuditAction.UPDATE,
            entity_name='Lead',
            record_id=lead.id,
            old_value=old_val,
            new_value=lead.to_dict(),
            details=f"Updated lead {lead.lead_code}",
            user_id=current_user.id
        )

        flash("Lead updated successfully.", "success")
        return redirect(url_for('leads.details', lead_id=lead.id))

    return render_template('leads/form.html', form=form, title='Edit Lead', lead=lead)

@lead_bp.route('/<int:lead_id>/delete', methods=['POST'])
@login_required
def delete(lead_id):
    lead = Lead.query.get_or_404(lead_id)

    if current_user.is_sales_executive and lead.assigned_to_id != current_user.id:
        flash("You are not authorized to delete this lead.", "danger")
        abort(403)

    old_val = lead.to_dict()
    code = lead.lead_code
    name = lead.lead_name

    db.session.delete(lead)
    db.session.commit()

    AuditService.log(
        action=AuditAction.DELETE,
        entity_name='Lead',
        record_id=lead_id,
        old_value=old_val,
        details=f"Deleted lead {code} ({name})",
        user_id=current_user.id
    )

    flash(f"Lead {name} ({code}) has been deleted.", "info")
    return redirect(url_for('leads.list_leads'))

@lead_bp.route('/<int:lead_id>/convert', methods=['POST'])
@login_required
def convert(lead_id):
    lead = Lead.query.get_or_404(lead_id)

    if current_user.is_sales_executive and lead.assigned_to_id != current_user.id:
        flash("You are not authorized to convert this lead.", "danger")
        abort(403)

    form = ConvertLeadForm()
    if form.validate_on_submit():
        opp_name = form.opportunity_name.data.strip() if form.opportunity_name.data else None
        amount = form.amount.data
        close_date = form.expected_close_date.data

        success, res = CRMService.convert_lead(
            lead_id=lead.id,
            user=current_user,
            opportunity_name=opp_name,
            amount=amount,
            expected_close_date=close_date
        )

        if success:
            cust = res['customer']
            opp = res['opportunity']
            msg = f"Lead {lead.lead_code} converted successfully! Created Customer {cust.customer_code}."
            if opp:
                msg += f" Created Opportunity {opp.opportunity_code} (${opp.amount:,.2f})."
            flash(msg, "success")
            return redirect(url_for('customers.details', customer_id=cust.id))
        else:
            flash(f"Conversion failed: {res}", "danger")
            return redirect(url_for('leads.details', lead_id=lead.id))
    else:
        for err in form.errors.values():
            flash(err[0], "danger")
        return redirect(url_for('leads.details', lead_id=lead.id))

