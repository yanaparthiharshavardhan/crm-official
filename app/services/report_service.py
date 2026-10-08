from datetime import datetime, date, timedelta
from sqlalchemy import func
from app.models import (
    db, Customer, Lead, LeadStatus, Opportunity, OpportunityStage, 
    OpportunityStatus, FollowUp, FollowUpStatus, Activity, User, AuditLog
)
from app.services.crm_service import CRMService

class ReportService:
    @staticmethod
    def get_dashboard_kpis(user, date_filter=None, start_date=None, end_date=None):
        """
        Computes role-based KPIs:
        - Total Customers
        - Total Leads
        - Open Leads (New, Contacted, Qualified)
        - Total Opportunities
        - Open Opportunities
        - Won Opportunities
        - Lost Opportunities
        - Total Pipeline Value (Sum of Open Opportunity Amounts)
        - Weighted Pipeline Value (Sum of Amount * Probability / 100)
        """
        cust_query = CRMService.get_scoped_customers(user)
        lead_query = CRMService.get_scoped_leads(user)
        opp_query = CRMService.get_scoped_opportunities(user)
        fu_query = CRMService.get_scoped_followups(user)

        # Apply date filters if provided
        s_date, e_date = ReportService.resolve_date_range(date_filter, start_date, end_date)
        if s_date and e_date:
            cust_query = cust_query.filter(func.date(Customer.created_date) >= s_date, func.date(Customer.created_date) <= e_date)
            lead_query = lead_query.filter(func.date(Lead.created_date) >= s_date, func.date(Lead.created_date) <= e_date)
            opp_query = opp_query.filter(func.date(Opportunity.created_date) >= s_date, func.date(Opportunity.created_date) <= e_date)
            fu_query = fu_query.filter(FollowUp.followup_date >= s_date, FollowUp.followup_date <= e_date)

        total_customers = cust_query.count()
        total_leads = lead_query.count()
        open_leads = lead_query.filter(Lead.status.in_([LeadStatus.NEW, LeadStatus.CONTACTED, LeadStatus.QUALIFIED])).count()
        
        all_opps = opp_query.all()
        total_opportunities = len(all_opps)
        open_opportunities = sum(1 for o in all_opps if o.stage not in [OpportunityStage.WON, OpportunityStage.LOST])
        won_opportunities = sum(1 for o in all_opps if o.stage == OpportunityStage.WON)
        lost_opportunities = sum(1 for o in all_opps if o.stage == OpportunityStage.LOST)
        
        pipeline_value = sum(o.amount for o in all_opps if o.stage not in [OpportunityStage.WON, OpportunityStage.LOST])
        weighted_pipeline_value = sum(o.weighted_amount for o in all_opps if o.stage not in [OpportunityStage.WON, OpportunityStage.LOST])
        won_value = sum(o.amount for o in all_opps if o.stage == OpportunityStage.WON)

        # Pending follow-ups & overdue
        pending_followups = fu_query.filter(FollowUp.status == FollowUpStatus.PLANNED).count()
        overdue_followups = fu_query.filter(FollowUp.status == FollowUpStatus.PLANNED, FollowUp.followup_date < date.today()).count()

        return {
            'total_customers': total_customers,
            'total_leads': total_leads,
            'open_leads': open_leads,
            'total_opportunities': total_opportunities,
            'open_opportunities': open_opportunities,
            'won_opportunities': won_opportunities,
            'lost_opportunities': lost_opportunities,
            'pipeline_value': round(pipeline_value, 2),
            'weighted_pipeline_value': round(weighted_pipeline_value, 2),
            'won_value': round(won_value, 2),
            'pending_followups': pending_followups,
            'overdue_followups': overdue_followups
        }

    @staticmethod
    def get_dashboard_chart_data(user, date_filter=None, start_date=None, end_date=None):
        """
        Generates Chart.js data objects for:
        1. Lead Status (New, Contacted, Qualified, Lost, Converted, Unqualified)
        2. Opportunity Pipeline (Qualification, Proposal, Negotiation, Won, Lost)
        3. Monthly Sales / Outcome trend
        """
        lead_query = CRMService.get_scoped_leads(user)
        opp_query = CRMService.get_scoped_opportunities(user)

        s_date, e_date = ReportService.resolve_date_range(date_filter, start_date, end_date)
        if s_date and e_date:
            lead_query = lead_query.filter(func.date(Lead.created_date) >= s_date, func.date(Lead.created_date) <= e_date)
            opp_query = opp_query.filter(func.date(Opportunity.created_date) >= s_date, func.date(Opportunity.created_date) <= e_date)

        # 1. Lead Status Data
        lead_statuses = [LeadStatus.NEW, LeadStatus.CONTACTED, LeadStatus.QUALIFIED, LeadStatus.UNQUALIFIED, LeadStatus.CONVERTED, LeadStatus.LOST]
        lead_counts = []
        for st in lead_statuses:
            lead_counts.append(lead_query.filter(Lead.status == st).count())

        lead_chart = {
            'labels': lead_statuses,
            'data': lead_counts,
            'backgroundColor': ['#0d6efd', '#0dcaf0', '#198754', '#6c757d', '#20c997', '#dc3545']
        }

        # 2. Opportunity Pipeline Data
        opp_stages = [OpportunityStage.QUALIFICATION, OpportunityStage.PROPOSAL, OpportunityStage.NEGOTIATION, OpportunityStage.WON, OpportunityStage.LOST]
        stage_amounts = []
        stage_counts = []
        all_opps = opp_query.all()
        for st in opp_stages:
            stage_opps = [o for o in all_opps if o.stage == st]
            stage_amounts.append(sum(o.amount for o in stage_opps))
            stage_counts.append(len(stage_opps))

        pipeline_chart = {
            'labels': opp_stages,
            'amounts': stage_amounts,
            'counts': stage_counts,
            'backgroundColor': ['#3b82f6', '#f59e0b', '#8b5cf6', '#10b981', '#ef4444']
        }

        # 3. Monthly Sales Trend (Last 6 months)
        months = []
        won_monthly = []
        pipeline_monthly = []
        today = date.today()
        for i in range(5, -1, -1):
            target_month = (today.replace(day=1) - timedelta(days=i*30)).replace(day=1)
            month_label = target_month.strftime('%b %Y')
            months.append(month_label)
            
            # Sum won in this month
            won_sum = sum(
                o.amount for o in all_opps 
                if o.stage == OpportunityStage.WON and o.expected_close_date and 
                o.expected_close_date.year == target_month.year and o.expected_close_date.month == target_month.month
            )
            won_monthly.append(round(won_sum, 2))

            pipe_sum = sum(
                o.amount for o in all_opps 
                if o.stage not in [OpportunityStage.WON, OpportunityStage.LOST] and o.expected_close_date and
                o.expected_close_date.year == target_month.year and o.expected_close_date.month == target_month.month
            )
            pipeline_monthly.append(round(pipe_sum, 2))

        sales_trend_chart = {
            'labels': months,
            'won': won_monthly,
            'pipeline': pipeline_monthly
        }

        return {
            'lead_chart': lead_chart,
            'pipeline_chart': pipeline_chart,
            'sales_trend_chart': sales_trend_chart
        }

    @staticmethod
    def resolve_date_range(filter_type, custom_start=None, custom_end=None):
        today = date.today()
        if filter_type == 'today':
            return today, today
        elif filter_type == 'week':
            start = today - timedelta(days=today.weekday())
            return start, today
        elif filter_type == 'month':
            start = today.replace(day=1)
            return start, today
        elif filter_type == 'custom' and custom_start and custom_end:
            try:
                s = datetime.strptime(custom_start, '%Y-%m-%d').date()
                e = datetime.strptime(custom_end, '%Y-%m-%d').date()
                return s, e
            except Exception:
                return None, None
        return None, None

    @staticmethod
    def get_pipeline_report(user):
        """Generates stage-wise and owner-wise pipeline breakdown."""
        opps = CRMService.get_scoped_opportunities(user).all()
        
        by_stage = {}
        for stage in OpportunityStage.ALL:
            by_stage[stage] = {'count': 0, 'total_amount': 0.0, 'weighted_amount': 0.0}
            
        by_owner = {}
        for o in opps:
            # stage breakdown
            if o.stage in by_stage:
                by_stage[o.stage]['count'] += 1
                by_stage[o.stage]['total_amount'] += o.amount
                by_stage[o.stage]['weighted_amount'] += o.weighted_amount

            # owner breakdown
            owner_name = o.assigned_to.name if o.assigned_to else 'Unassigned'
            if owner_name not in by_owner:
                by_owner[owner_name] = {'count': 0, 'total_amount': 0.0, 'won_amount': 0.0, 'weighted_amount': 0.0}
            by_owner[owner_name]['count'] += 1
            by_owner[owner_name]['total_amount'] += o.amount
            by_owner[owner_name]['weighted_amount'] += o.weighted_amount
            if o.stage == OpportunityStage.WON:
                by_owner[owner_name]['won_amount'] += o.amount

        return {'by_stage': by_stage, 'by_owner': by_owner, 'opportunities': opps}

