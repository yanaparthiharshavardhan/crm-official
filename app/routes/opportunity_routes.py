from datetime import date
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from sqlalchemy import or_
from app.models import (
    db, Opportunity, OpportunityStage, OpportunityStatus, AuditAction, Customer, User
)
from app.forms import OpportunityForm
from app.services.crm_service import CRMService
from app.services.audit_service import AuditService

opportunity_bp = Blueprint('opportunities', __name__, url_prefix='/opportunities')

@opportunity_bp.route('/')
@login_required
def list_opportunities():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '').strip()
    stage = request.args.get('stage', '').strip()
    status = request.args.get('status', '').strip()
    view_type = request.args.get('view', 'table') # 'table' or 'pipeline'

    query = CRMService.get_scoped_opportunities(current_user)

    if search:
        search_fmt = f"%{search}%"
        query = query.join(Customer, Opportunity.customer_id == Customer.id, isouter=True).filter(
            or_(
                Opportunity.opportunity_name.ilike(search_fmt),
                Opportunity.opportunity_code.ilike(search_fmt),
                Customer.customer_name.ilike(search_fmt),
                Opportunity.stage.ilike(search_fmt)
            )
        )

    if stage:
        query = query.filter(Opportunity.stage == stage)

    if status:
        query = query.filter(Opportunity.status == status)

    if view_type == 'pipeline':
        all_opps = query.order_by(Opportunity.expected_close_date.asc()).all()
        stage_map = {s: [] for s in OpportunityStage.ALL}
        for opp in all_opps:
            if opp.stage in stage_map:
                stage_map[opp.stage].append(opp)
        return render_template(
            'opportunities/pipeline_view.html',
            stage_map=stage_map,
            stages=OpportunityStage.ALL,
            search=search,
            stage=stage,
            status=status
        )

    opportunities_page = query.order_by(Opportunity.created_date.desc()).paginate(page=page, per_page=10, error_out=False)

    return render_template(
        'opportunities/index.html',
        opportunities_page=opportunities_page,
        search=search,
        stage=stage,
        status=status,
        stages=OpportunityStage.ALL,
        statuses=OpportunityStatus.CHOICES
    )

@opportunity_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    form = OpportunityForm()
    
    # Pre-select customer if passed in query string
    customer_id = request.args.get('customer_id', type=int)
    if request.method == 'GET' and customer_id:
        form.customer_id.data = customer_id

    if form.validate_on_submit():
        # Server-side Business validation
        is_valid, err_msg = CRMService.validate_opportunity(
            amount=form.amount.data,
            probability=form.probability.data,
            expected_close_date=form.expected_close_date.data,
            stage=form.stage.data
        )
        if not is_valid:
            flash(err_msg, 'danger')
            return render_template('opportunities/form.html', form=form, title='Create Opportunity')

        # Determine status from stage
        status = OpportunityStatus.OPEN
        if form.stage.data == OpportunityStage.WON:
            status = OpportunityStatus.WON
        elif form.stage.data == OpportunityStage.LOST:
            status = OpportunityStatus.LOST

        opp = Opportunity(
            opportunity_code=CRMService.generate_opportunity_code(),
            opportunity_name=form.opportunity_name.data.strip(),
            customer_id=form.customer_id.data,
            amount=float(form.amount.data),
            stage=form.stage.data,
            probability=form.probability.data,
            expected_close_date=form.expected_close_date.data,
            status=status,
            source=form.source.data.strip() if form.source.data else None,
            notes=form.notes.data.strip() if form.notes.data else None,
            assigned_to_id=form.assigned_to_id.data if form.assigned_to_id.data > 0 else (current_user.id if current_user.is_sales_executive else None)
        )
        db.session.add(opp)
        db.session.commit()

        AuditService.log(
            action=AuditAction.CREATE,
            entity_name='Opportunity',
            record_id=opp.id,
            new_value=opp.to_dict(),
            details=f"Created opportunity {opp.opportunity_code} (${opp.amount:,.2f})",
            user_id=current_user.id
        )

        flash(f"Opportunity {opp.opportunity_name} ({opp.opportunity_code}) created successfully.", 'success')
        return redirect(url_for('opportunities.details', opportunity_id=opp.id))

    return render_template('opportunities/form.html', form=form, title='Create Opportunity')

@opportunity_bp.route('/<int:opportunity_id>')
@login_required
def details(opportunity_id):
    opp = Opportunity.query.get_or_404(opportunity_id)

    if current_user.is_sales_executive and opp.assigned_to_id != current_user.id:
        flash("You are not authorized to view this opportunity.", "danger")
        abort(403)

    return render_template('opportunities/details.html', opportunity=opp, stages=OpportunityStage.ALL)

@opportunity_bp.route('/<int:opportunity_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(opportunity_id):
    opp = Opportunity.query.get_or_404(opportunity_id)

    if current_user.is_sales_executive and opp.assigned_to_id != current_user.id:
        flash("You are not authorized to edit this opportunity.", "danger")
        abort(403)

    form = OpportunityForm(obj=opp)
    if form.validate_on_submit():
        # Server-side Business validation
        is_valid, err_msg = CRMService.validate_opportunity(
            amount=form.amount.data,
            probability=form.probability.data,
            expected_close_date=form.expected_close_date.data,
            stage=form.stage.data
        )
        if not is_valid:
            flash(err_msg, 'danger')
            return render_template('opportunities/form.html', form=form, title='Edit Opportunity', opportunity=opp)

        old_val = opp.to_dict()

        opp.opportunity_name = form.opportunity_name.data.strip()
        opp.customer_id = form.customer_id.data
        opp.amount = float(form.amount.data)
        opp.stage = form.stage.data
        opp.probability = form.probability.data
        opp.expected_close_date = form.expected_close_date.data
        opp.source = form.source.data.strip() if form.source.data else None
        opp.notes = form.notes.data.strip() if form.notes.data else None

        if form.stage.data == OpportunityStage.WON:
            opp.status = OpportunityStatus.WON
        elif form.stage.data == OpportunityStage.LOST:
            opp.status = OpportunityStatus.LOST
        else:
            opp.status = OpportunityStatus.OPEN

        if not current_user.is_sales_executive or current_user.is_admin or current_user.is_manager:
            opp.assigned_to_id = form.assigned_to_id.data if form.assigned_to_id.data > 0 else None

        db.session.commit()

        AuditService.log(
            action=AuditAction.UPDATE,
            entity_name='Opportunity',
            record_id=opp.id,
            old_value=old_val,
            new_value=opp.to_dict(),
            details=f"Updated opportunity {opp.opportunity_code} - Stage: {opp.stage}, Amount: ${opp.amount}",
            user_id=current_user.id
        )

        flash("Opportunity updated successfully.", "success")
        return redirect(url_for('opportunities.details', opportunity_id=opp.id))

    return render_template('opportunities/form.html', form=form, title='Edit Opportunity', opportunity=opp)

@opportunity_bp.route('/<int:opportunity_id>/delete', methods=['POST'])
@login_required
def delete(opportunity_id):
    opp = Opportunity.query.get_or_404(opportunity_id)

    if current_user.is_sales_executive and opp.assigned_to_id != current_user.id:
        flash("You are not authorized to delete this opportunity.", "danger")
        abort(403)

    old_val = opp.to_dict()
    code = opp.opportunity_code
    name = opp.opportunity_name

    db.session.delete(opp)
    db.session.commit()

    AuditService.log(
        action=AuditAction.DELETE,
        entity_name='Opportunity',
        record_id=opportunity_id,
        old_value=old_val,
        details=f"Deleted opportunity {code} ({name})",
        user_id=current_user.id
    )

    flash(f"Opportunity {name} ({code}) has been deleted.", "info")
    return redirect(url_for('opportunities.list_opportunities'))

@opportunity_bp.route('/<int:opportunity_id>/stage', methods=['POST'])
@login_required
def update_stage(opportunity_id):
    opp = Opportunity.query.get_or_404(opportunity_id)

    if current_user.is_sales_executive and opp.assigned_to_id != current_user.id:
        flash("You are not authorized to modify this opportunity.", "danger")
        abort(403)

    new_stage = request.form.get('stage')
    if new_stage in OpportunityStage.ALL:
        old_stage = opp.stage
        opp.stage = new_stage
        
        # Auto adjust probability default according to stage
        opp.probability = OpportunityStage.STAGE_PROBABILITY_MAP.get(new_stage, opp.probability)

        if new_stage == OpportunityStage.WON:
            opp.status = OpportunityStatus.WON
        elif new_stage == OpportunityStage.LOST:
            opp.status = OpportunityStatus.LOST
        else:
            opp.status = OpportunityStatus.OPEN

        db.session.commit()

        AuditService.log(
            action=AuditAction.UPDATE,
            entity_name='Opportunity',
            record_id=opp.id,
            old_value={'stage': old_stage},
            new_value={'stage': new_stage, 'probability': opp.probability, 'status': opp.status},
            details=f"Changed stage of {opp.opportunity_code} from {old_stage} to {new_stage}",
            user_id=current_user.id
        )
        flash(f"Stage updated to {new_stage}.", "success")
    else:
        flash("Invalid stage selected.", "danger")

    return redirect(request.referrer or url_for('opportunities.details', opportunity_id=opp.id))

