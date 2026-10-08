import unittest
from datetime import date, timedelta
from app import create_app
from app.config import Config
from app.models import (
    db, User, Role, Customer, Lead, LeadStatus, LeadPriority, LeadSource,
    Opportunity, OpportunityStage, OpportunityStatus, AuditLog, AuditAction
)
from app.services.auth_service import AuthService
from app.services.crm_service import CRMService

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False

class WorkflowsTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()

        self.user, _ = AuthService.create_user("Workflow Rep", "workflow@test.com", "Sales@123", Role.SALES_EXECUTIVE)

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_lead_to_customer_conversion(self):
        """Tests complete lead conversion workflow into a Customer and Opportunity with Audit log."""
        lead = Lead(
            lead_code="LEAD-0001",
            lead_name="Prospective Buyer",
            email="buyer@prospective.com",
            phone="9876543233",
            company_name="Prospective Industries",
            source=LeadSource.WEBSITE,
            status=LeadStatus.QUALIFIED,
            priority=LeadPriority.HIGH,
            expected_value=75000.0,
            assigned_to_id=self.user.id
        )
        db.session.add(lead)
        db.session.commit()

        # Convert Lead
        success, res = CRMService.convert_lead(
            lead_id=lead.id,
            user=self.user,
            opportunity_name="Prospective Core Platform License",
            amount=75000.0,
            expected_close_date=date.today() + timedelta(days=30)
        )

        self.assertTrue(success)
        customer = res['customer']
        opportunity = res['opportunity']

        # Verify created customer
        self.assertIsNotNone(customer)
        self.assertEqual(customer.email, "buyer@prospective.com")
        self.assertEqual(customer.customer_name, "Prospective Buyer")
        self.assertEqual(customer.company_name, "Prospective Industries")

        # Verify created opportunity
        self.assertIsNotNone(opportunity)
        self.assertEqual(opportunity.amount, 75000.0)
        self.assertEqual(opportunity.stage, OpportunityStage.QUALIFICATION)
        self.assertEqual(opportunity.weighted_amount, (75000.0 * 20) / 100.0) # 20% prob default

        # Verify Lead is marked as Converted
        updated_lead = Lead.query.get(lead.id)
        self.assertEqual(updated_lead.status, LeadStatus.CONVERTED)
        self.assertEqual(updated_lead.converted_customer_id, customer.id)
        self.assertEqual(updated_lead.converted_opportunity_id, opportunity.id)

        # Verify Audit Log entry generated
        convert_log = AuditLog.query.filter_by(action=AuditAction.CONVERT, entity_name='Lead').first()
        self.assertIsNotNone(convert_log)
        self.assertEqual(convert_log.record_id, str(lead.id))

    def test_weighted_pipeline_calculation(self):
        """Derived weighted pipeline = Amount * Probability / 100."""
        opp = Opportunity(
            opportunity_code="OPP-0001",
            opportunity_name="Big Deal",
            amount=100000.0,
            probability=80,
            stage=OpportunityStage.NEGOTIATION,
            expected_close_date=date.today() + timedelta(days=10)
        )
        self.assertEqual(opp.weighted_amount, 80000.0)

if __name__ == '__main__':
    unittest.main()

