import csv
import io
from datetime import datetime, date
from flask import Blueprint, render_template, request, Response, abort
from flask_login import login_required, current_user
from sqlalchemy import func
from app.models import (
    Customer, Lead, LeadStatus, Opportunity, OpportunityStage, 
    FollowUp, FollowUpStatus, Activity, User, AuditLog, Role
)
from app.services.crm_service import CRMService
from app.services.report_service import ReportService
from app.routes.auth_routes import roles_required

report_bp = Blueprint('reports', __name__, url_prefix='/reports')

@report_bp.route('/')
@login_required
def hub():
    return render_template('reports/hub.html')

@report_bp.route('/customers')
@login_required
def customers_report():
    query = CRMService.get_scoped_customers(current_user)
    
    status = request.args.get('status', '').strip()
    if status:
        query = query.filter(Customer.status == status)

    customers = query.order_by(Customer.created_date.desc()).all()

    if request.args.get('export') == 'csv':
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Customer Code', 'Customer Name', 'Email', 'Phone', 'Company', 'Status', 'Owner', 'Created Date'])
        for c in customers:
            writer.writerow([
                c.customer_code, c.customer_name, c.email, c.phone, c.company_name,
                c.status, c.owner.name if c.owner else 'Unassigned',
                c.created_date.strftime('%Y-%m-%d %H:%M') if c.created_date else ''
            ])
        return Response(output.getvalue(), mimetype='text/csv', headers={"Content-Disposition": "attachment;filename=customers_report.csv"})

    return render_template('reports/customers.html', customers=customers, status=status)

@report_bp.route('/leads')
@login_required
def leads_report():
    query = CRMService.get_scoped_leads(current_user)

    status = request.args.get('status', '').strip()
    source = request.args.get('source', '').strip()
    if status:
        query = query.filter(Lead.status == status)
    if source:
        query = query.filter(Lead.source == source)

    leads = query.order_by(Lead.created_date.desc()).all()

    total_leads = len(leads)
    converted_leads = sum(1 for l in leads if l.status == LeadStatus.CONVERTED)
    conv_rate = round((converted_leads / total_leads * 100), 1) if total_leads > 0 else 0

    if request.args.get('export') == 'csv':
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Lead Code', 'Lead Name', 'Email', 'Phone', 'Company', 'Source', 'Status', 'Priority', 'Expected Value', 'Assigned To', 'Created Date'])
        for l in leads:
            writer.writerow([
                l.lead_code, l.lead_name, l.email, l.phone, l.company_name,
                l.source, l.status, l.priority, l.expected_value,
                l.assigned_to.name if l.assigned_to else 'Unassigned',
                l.created_date.strftime('%Y-%m-%d %H:%M') if l.created_date else ''
            ])
        return Response(output.getvalue(), mimetype='text/csv', headers={"Content-Disposition": "attachment;filename=leads_report.csv"})

    return render_template('reports/leads.html', leads=leads, total_leads=total_leads, converted_leads=converted_leads, conv_rate=conv_rate, status=status, source=source)

@report_bp.route('/followups')
@login_required
def followups_report():
    query = CRMService.get_scoped_followups(current_user)
    today = date.today()

    status = request.args.get('status', '').strip()
    if status:
        query = query.filter(FollowUp.status == status)

    followups = query.order_by(FollowUp.followup_date.desc()).all()

    planned = sum(1 for f in followups if f.status == FollowUpStatus.PLANNED and f.followup_date >= today)
    overdue = sum(1 for f in followups if f.status == FollowUpStatus.PLANNED and f.followup_date < today)
    completed = sum(1 for f in followups if f.status == FollowUpStatus.COMPLETED)
    missed = sum(1 for f in followups if f.status == FollowUpStatus.MISSED)

    if request.args.get('export') == 'csv':
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['ID', 'Subject', 'Type', 'Date', 'Status', 'Overdue?', 'Related Record', 'Assigned To', 'Remarks'])
        for f in followups:
            writer.writerow([
                f.id, f.subject, f.followup_type, f.followup_date.strftime('%Y-%m-%d'),
                f.status, 'Yes' if f.is_overdue else 'No',
                f.related_entity_display,
                f.assigned_to.name if f.assigned_to else 'Unassigned',
                f.remarks or ''
            ])
        return Response(output.getvalue(), mimetype='text/csv', headers={"Content-Disposition": "attachment;filename=followups_report.csv"})

    return render_template('reports/followups.html', followups=followups, planned=planned, overdue=overdue, completed=completed, missed=missed, today=today, status=status)

@report_bp.route('/opportunities')
@login_required
def opportunities_report():
    query = CRMService.get_scoped_opportunities(current_user)

    stage = request.args.get('stage', '').strip()
    if stage:
        query = query.filter(Opportunity.stage == stage)

    opportunities = query.order_by(Opportunity.expected_close_date.asc()).all()

    total_amount = sum(o.amount for o in opportunities)
    weighted_amount = sum(o.weighted_amount for o in opportunities)

    if request.args.get('export') == 'csv':
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Opportunity Code', 'Opportunity Name', 'Customer', 'Stage', 'Amount', 'Probability (%)', 'Weighted Amount', 'Expected Close Date', 'Assigned To', 'Status'])
        for o in opportunities:
            writer.writerow([
                o.opportunity_code, o.opportunity_name,
                o.customer.customer_name if o.customer else 'N/A',
                o.stage, o.amount, o.probability, o.weighted_amount,
                o.expected_close_date.strftime('%Y-%m-%d') if o.expected_close_date else '',
                o.assigned_to.name if o.assigned_to else 'Unassigned',
                o.status
            ])
        return Response(output.getvalue(), mimetype='text/csv', headers={"Content-Disposition": "attachment;filename=opportunities_report.csv"})

    return render_template('reports/opportunities.html', opportunities=opportunities, total_amount=total_amount, weighted_amount=weighted_amount, stage=stage, stages=OpportunityStage.ALL)

@report_bp.route('/pipeline')
@login_required
def pipeline_report():
    data = ReportService.get_pipeline_report(current_user)

    if request.args.get('export') == 'csv':
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Stage', 'Count', 'Total Amount ($)', 'Weighted Amount ($)'])
        for stage, val in data['by_stage'].items():
            writer.writerow([stage, val['count'], f"{val['total_amount']:.2f}", f"{val['weighted_amount']:.2f}"])
        return Response(output.getvalue(), mimetype='text/csv', headers={"Content-Disposition": "attachment;filename=pipeline_report.csv"})

    return render_template('reports/pipeline.html', data=data)

@report_bp.route('/conversions')
@login_required
def conversion_report():
    query = CRMService.get_scoped_leads(current_user)
    all_leads = query.all()
    
    total = len(all_leads)
    converted = [l for l in all_leads if l.status == LeadStatus.CONVERTED]
    lost = [l for l in all_leads if l.status == LeadStatus.LOST]
    open_leads = [l for l in all_leads if l.status in [LeadStatus.NEW, LeadStatus.CONTACTED, LeadStatus.QUALIFIED]]

    rate = round((len(converted) / total * 100), 1) if total > 0 else 0

    # Source-wise conversion breakdown
    by_source = {}
    for l in all_leads:
        if l.source not in by_source:
            by_source[l.source] = {'total': 0, 'converted': 0}
        by_source[l.source]['total'] += 1
        if l.status == LeadStatus.CONVERTED:
            by_source[l.source]['converted'] += 1

    return render_template(
        'reports/conversions.html',
        total=total,
        converted_count=len(converted),
        lost_count=len(lost),
        open_count=len(open_leads),
        rate=rate,
        by_source=by_source
    )

@report_bp.route('/user-activity')
@login_required
@roles_required(Role.ADMIN, Role.MANAGER)
def user_activity_report():
    users = User.query.filter(User.is_active == True).order_by(User.name).all()
    user_stats = []

    for u in users:
        cust_cnt = Customer.query.filter(Customer.owner_id == u.id).count()
        lead_cnt = Lead.query.filter(Lead.assigned_to_id == u.id).count()
        opp_cnt = Opportunity.query.filter(Opportunity.assigned_to_id == u.id).count()
        opp_won = Opportunity.query.filter(Opportunity.assigned_to_id == u.id, Opportunity.stage == OpportunityStage.WON).count()
        fu_cnt = FollowUp.query.filter(FollowUp.assigned_to_id == u.id, FollowUp.status == FollowUpStatus.COMPLETED).count()
        act_cnt = Activity.query.filter(Activity.assigned_to_id == u.id).count()
        
        user_stats.append({
            'user': u,
            'customers': cust_cnt,
            'leads': lead_cnt,
            'opportunities': opp_cnt,
            'won_deals': opp_won,
            'completed_followups': fu_cnt,
            'logged_activities': act_cnt
        })

    if request.args.get('export') == 'csv':
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['User Name', 'Email', 'Role', 'Assigned Customers', 'Assigned Leads', 'Total Opps', 'Won Deals', 'Completed FollowUps', 'Activities'])
        for s in user_stats:
            writer.writerow([
                s['user'].name, s['user'].email, s['user'].role,
                s['customers'], s['leads'], s['opportunities'], s['won_deals'],
                s['completed_followups'], s['logged_activities']
            ])
        return Response(output.getvalue(), mimetype='text/csv', headers={"Content-Disposition": "attachment;filename=user_activity_report.csv"})

    return render_template('reports/user_activity.html', user_stats=user_stats)

