import unittest
from datetime import date, timedelta
from app import create_app
from app.config import Config
from app.models import db, User, Role, Customer, Opportunity, OpportunityStage, FollowUp, FollowUpStatus
from app.services.crm_service import CRMService

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False

class ValidationTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_opportunity_amount_validation(self):
        """Opportunity Amount <= 0 must be rejected."""
        valid, msg = CRMService.validate_opportunity(
            amount=0,
            probability=50,
            expected_close_date=date.today() + timedelta(days=5),
            stage=OpportunityStage.QUALIFICATION
        )
        self.assertFalse(valid)
        self.assertIn("must be greater than 0", msg)

        valid_neg, msg_neg = CRMService.validate_opportunity(
            amount=-100,
            probability=50,
            expected_close_date=date.today() + timedelta(days=5),
            stage=OpportunityStage.QUALIFICATION
        )
        self.assertFalse(valid_neg)

    def test_opportunity_probability_validation(self):
        """Opportunity probability > 100 or < 0 must be rejected."""
        valid_over, msg = CRMService.validate_opportunity(
            amount=1000,
            probability=101,
            expected_close_date=date.today() + timedelta(days=5),
            stage=OpportunityStage.QUALIFICATION
        )
        self.assertFalse(valid_over)
        self.assertIn("between 0 and 100", msg)

        valid_under, _ = CRMService.validate_opportunity(
            amount=1000,
            probability=-5,
            expected_close_date=date.today() + timedelta(days=5),
            stage=OpportunityStage.QUALIFICATION
        )
        self.assertFalse(valid_under)

    def test_opportunity_close_date_validation(self):
        """Expected Close Date in the past must be rejected for active opportunities."""
        yesterday = date.today() - timedelta(days=1)
        valid, msg = CRMService.validate_opportunity(
            amount=5000,
            probability=50,
            expected_close_date=yesterday,
            stage=OpportunityStage.PROPOSAL
        )
        self.assertFalse(valid)
        self.assertIn("cannot be in the past", msg)

        # For Won / Lost, past dates are acceptable as historical outcomes
        valid_won, _ = CRMService.validate_opportunity(
            amount=5000,
            probability=100,
            expected_close_date=yesterday,
            stage=OpportunityStage.WON
        )
        self.assertTrue(valid_won)

    def test_followup_date_validation(self):
        """Follow-up date cannot be earlier than today for a new/planned follow-up."""
        yesterday = date.today() - timedelta(days=1)
        valid, msg = CRMService.validate_followup_date(yesterday, FollowUpStatus.PLANNED)
        self.assertFalse(valid)
        self.assertIn("cannot be earlier than today", msg)

        tomorrow = date.today() + timedelta(days=1)
        valid_ok, _ = CRMService.validate_followup_date(tomorrow, FollowUpStatus.PLANNED)
        self.assertTrue(valid_ok)

    def test_duplicate_customer_detection(self):
        """Duplicate customer email or phone must be prevented."""
        c = Customer(
            customer_code="CUST-0001",
            customer_name="Existing Co",
            email="existing@co.com",
            phone="9876543210",
            company_name="Existing Co"
        )
        db.session.add(c)
        db.session.commit()

        # Duplicate email
        is_unique_email, msg1 = CRMService.check_duplicate_customer("existing@co.com", "9876543299")
        self.assertFalse(is_unique_email)
        self.assertIn("email address already exists", msg1)

        # Duplicate phone
        is_unique_phone, msg2 = CRMService.check_duplicate_customer("new@co.com", "9876543210")
        self.assertFalse(is_unique_phone)
        self.assertIn("phone number already exists", msg2)

        # Unique
        is_unique_ok, _ = CRMService.check_duplicate_customer("unique@co.com", "9876543299")
        self.assertTrue(is_unique_ok)

if __name__ == '__main__':
    unittest.main()

