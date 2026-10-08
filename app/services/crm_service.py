from datetime import datetime, date
from sqlalchemy import or_
from app.models import (
    db, User, Role, Customer, Lead, LeadStatus, Opportunity, OpportunityStage, 
    OpportunityStatus, FollowUp, FollowUpStatus, Activity, AuditAction
)
from app.services.audit_service import AuditService

class CRMService:
    # ----------------------------------------------------
    # Sequence Code Generators
    # ----------------------------------------------------
    @staticmethod
    def generate_customer_code():
        last = Customer.query.order_by(Customer.id.desc()).first()
        next_id = (last.id + 1) if last else 1
        return f"CUST-{next_id:04d}"

    @staticmethod
    def generate_lead_code():
        last = Lead.query.order_by(Lead.id.desc()).first()
        next_id = (last.id + 1) if last else 1
        return f"LEAD-{next_id:04d}"

    @staticmethod
    def generate_opportunity_code():
        last = Opportunity.query.order_by(Opportunity.id.desc()).first()
        next_id = (last.id + 1) if last else 1
        return f"OPP-{next_id:04d}"

    # ----------------------------------------------------
    # Scoped Queries for RBAC
    # ----------------------------------------------------
    @staticmethod
    def get_scoped_customers(user):
        """Admin & Manager see all customers; SalesExecutive sees only assigned."""
        if user.is_admin or user.is_manager:
            return Customer.query
        return Customer.query.filter(Customer.owner_id == user.id)

    @staticmethod
    def get_scoped_leads(user):
        """Admin & Manager see all leads; SalesExecutive sees only assigned."""
        if user.is_admin or user.is_manager:
            return Lead.query
        return Lead.query.filter(Lead.assigned_to_id == user.id)

    @staticmethod
    def get_scoped_opportunities(user):
        """Admin & Manager see all opportunities; SalesExecutive sees only assigned."""
        if user.is_admin or user.is_manager:
            return Opportunity.query
        return Opportunity.query.filter(Opportunity.assigned_to_id == user.id)

    @staticmethod
    def get_scoped_followups(user):
        """Admin & Manager see all followups; SalesExecutive sees only assigned."""
        if user.is_admin or user.is_manager:
            return FollowUp.query
        return FollowUp.query.filter(FollowUp.assigned_to_id == user.id)

    @staticmethod
    def get_scoped_activities(user):
        """Admin & Manager see all activities; SalesExecutive sees only assigned."""
        if user.is_admin or user.is_manager:
            return Activity.query
        return Activity.query.filter(Activity.assigned_to_id == user.id)

    # ----------------------------------------------------
    # Business Validations
    # ----------------------------------------------------
    @staticmethod
    def check_duplicate_customer(email, phone, exclude_id=None):
        """Checks whether a customer already exists with the same email or phone."""
        query_email = Customer.query.filter(Customer.email == email.strip().lower())
        query_phone = Customer.query.filter(Customer.phone == phone.strip())
        if exclude_id:
            query_email = query_email.filter(Customer.id != exclude_id)
            query_phone = query_phone.filter(Customer.id != exclude_id)
        
        if query_email.first():
            return False, "A customer with this email address already exists."
        if query_phone.first():
            return False, "A customer with this phone number already exists."
        return True, ""

    @staticmethod
    def validate_opportunity(amount, probability, expected_close_date, stage):
        """
        Validates opportunity business rules:
        - Amount must be greater than 0 for active sales opportunities
        - Probability must be between 0 and 100 inclusive
        - Expected Close Date cannot be in the past for active opportunities
        """
        if amount is None or amount <= 0:
            return False, "Opportunity Amount must be greater than 0."
        if probability is None or probability < 0 or probability > 100:
            return False, "Probability must be between 0 and 100."
        
        # Date validation for active (non-lost, non-won) opportunities
        if stage not in [OpportunityStage.WON, OpportunityStage.LOST]:
            if isinstance(expected_close_date, str):
                expected_close_date = datetime.strptime(expected_close_date, '%Y-%m-%d').date()
            if expected_close_date < date.today():
                return False, "Expected Close Date cannot be in the past."
                
        return True, ""

    @staticmethod
    def validate_followup_date(followup_date, status):
        """Follow-up date cannot be earlier than today for a new/planned follow-up."""
        if status == FollowUpStatus.PLANNED:
            if isinstance(followup_date, str):
                followup_date = datetime.strptime(followup_date, '%Y-%m-%d').date()
            if followup_date < date.today():
                return False, "Follow-up date cannot be earlier than today."
        return True, ""

    # ----------------------------------------------------
    # Core CRM Workflows: Lead Conversion
    # ----------------------------------------------------
    @staticmethod
    def convert_lead(lead_id, user, opportunity_name=None, amount=None, expected_close_date=None):
        """
        Converts a Lead into a Customer and optionally creates an Opportunity.
        Marks lead as Converted, logs in Audit trail.
        """
        lead = Lead.query.get(lead_id)
        if not lead:
            return False, "Lead not found."
        
        if lead.status == LeadStatus.CONVERTED:
            return False, "Lead has already been converted."

        # Check if customer already exists for this email/phone
        existing_cust = Customer.query.filter(
            or_(Customer.email == lead.email, Customer.phone == lead.phone)
        ).first()

        if existing_cust:
            customer = existing_cust
        else:
            customer = Customer(
                customer_code=CRMService.generate_customer_code(),
                customer_name=lead.lead_name,
                email=lead.email,
                phone=lead.phone,
                company_name=lead.company_name,
                status='Active',
                notes=f"Converted from Lead {lead.lead_code}.\n{lead.notes or ''}",
                owner_id=lead.assigned_to_id or user.id,
                created_by_id=user.id
            )
            db.session.add(customer)
            db.session.flush() # obtain customer.id

            AuditService.log(
                action=AuditAction.CREATE,
                entity_name='Customer',
                record_id=customer.id,
                new_value=customer.to_dict(),
                details=f"Customer created via Lead conversion from {lead.lead_code}",
                user_id=user.id
            )

        opportunity = None
        if opportunity_name and amount:
            if expected_close_date is None:
                expected_close_date = date.today()
            
            opportunity = Opportunity(
                opportunity_code=CRMService.generate_opportunity_code(),
                opportunity_name=opportunity_name,
                customer_id=customer.id,
                lead_id=lead.id,
                amount=float(amount),
                stage=OpportunityStage.QUALIFICATION,
                probability=20,
                expected_close_date=expected_close_date,
                status=OpportunityStatus.OPEN,
                source=lead.source,
                notes=f"Created upon converting Lead {lead.lead_code}",
                assigned_to_id=customer.owner_id
            )
            db.session.add(opportunity)
            db.session.flush()

            AuditService.log(
                action=AuditAction.CREATE,
                entity_name='Opportunity',
                record_id=opportunity.id,
                new_value=opportunity.to_dict(),
                details=f"Opportunity created via Lead conversion from {lead.lead_code}",
                user_id=user.id
            )

        old_lead_status = lead.status
        lead.status = LeadStatus.CONVERTED
        lead.converted_customer_id = customer.id
        if opportunity:
            lead.converted_opportunity_id = opportunity.id

        db.session.commit()

        AuditService.log(
            action=AuditAction.CONVERT,
            entity_name='Lead',
            record_id=lead.id,
            old_value={'status': old_lead_status},
            new_value={'status': LeadStatus.CONVERTED, 'customer_id': customer.id, 'opportunity_id': opportunity.id if opportunity else None},
            details=f"Lead {lead.lead_code} converted to Customer {customer.customer_code}",
            user_id=user.id
        )

        return True, {"customer": customer, "opportunity": opportunity}

