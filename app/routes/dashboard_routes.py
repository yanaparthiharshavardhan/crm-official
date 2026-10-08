import json
from datetime import date
from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
from app.models import FollowUp, FollowUpStatus, Activity
from app.services.crm_service import CRMService
from app.services.report_service import ReportService

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@dashboard_bp.route('/dashboard')
@login_required
def index():
    date_filter = request.args.get('filter', 'all')
    custom_start = request.args.get('start_date')
    custom_end = request.args.get('end_date')

    kpis = ReportService.get_dashboard_kpis(
        user=current_user,
        date_filter=date_filter,
        start_date=custom_start,
        end_date=custom_end
    )

    chart_data = ReportService.get_dashboard_chart_data(
        user=current_user,
        date_filter=date_filter,
        start_date=custom_start,
        end_date=custom_end
    )

    # Scoped upcoming follow-ups
    upcoming_followups = CRMService.get_scoped_followups(current_user).filter(
        FollowUp.status == FollowUpStatus.PLANNED
    ).order_by(FollowUp.followup_date.asc()).limit(5).all()

    # Scoped recent activities
    recent_activities = CRMService.get_scoped_activities(current_user).order_by(
        Activity.activity_date.desc(), Activity.id.desc()
    ).limit(5).all()

    return render_template(
        'dashboard/index.html',
        kpis=kpis,
        chart_data=chart_data,
        chart_data_json=json.dumps(chart_data),
        upcoming_followups=upcoming_followups,
        recent_activities=recent_activities,
        date_filter=date_filter,
        custom_start=custom_start,
        custom_end=custom_end,
        today=date.today()
    )

