import unittest
from app import create_app
from app.config import Config
from app.models import db, User, Role, Customer
from app.services.auth_service import AuthService
from app.services.crm_service import CRMService

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False

class RBACTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()

        # Seed 3 users with different roles
        self.admin, _ = AuthService.create_user("Admin User", "admin@test.com", "Admin@123", Role.ADMIN)
        self.manager, _ = AuthService.create_user("Manager User", "manager@test.com", "Manager@123", Role.MANAGER)
        self.sales1, _ = AuthService.create_user("Sales Rep 1", "sales1@test.com", "Sales@123", Role.SALES_EXECUTIVE)
        self.sales2, _ = AuthService.create_user("Sales Rep 2", "sales2@test.com", "Sales@123", Role.SALES_EXECUTIVE)

        # Seed customers
        self.c1 = Customer(customer_code="CUST-0001", customer_name="Customer 1", email="c1@test.com", phone="9876543201", company_name="Co 1", owner_id=self.sales1.id)
        self.c2 = Customer(customer_code="CUST-0002", customer_name="Customer 2", email="c2@test.com", phone="9876543202", company_name="Co 2", owner_id=self.sales2.id)
        db.session.add_all([self.c1, self.c2])
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_anonymous_redirect(self):
        """Unauthenticated requests to protected pages must be redirected to login."""
        res = self.client.get('/')
        self.assertEqual(res.status_code, 302)
        self.assertIn('/login', res.headers['Location'])

        res2 = self.client.get('/customers/')
        self.assertEqual(res2.status_code, 302)

    def test_sales_rep_scoping(self):
        """Sales reps can only see their own assigned customers."""
        scoped_for_sales1 = CRMService.get_scoped_customers(self.sales1).all()
        self.assertEqual(len(scoped_for_sales1), 1)
        self.assertEqual(scoped_for_sales1[0].id, self.c1.id)

        scoped_for_sales2 = CRMService.get_scoped_customers(self.sales2).all()
        self.assertEqual(len(scoped_for_sales2), 1)
        self.assertEqual(scoped_for_sales2[0].id, self.c2.id)

    def test_manager_and_admin_scoping(self):
        """Managers and Admins see all customers across the organization."""
        scoped_for_manager = CRMService.get_scoped_customers(self.manager).all()
        self.assertEqual(len(scoped_for_manager), 2)

        scoped_for_admin = CRMService.get_scoped_customers(self.admin).all()
        self.assertEqual(len(scoped_for_admin), 2)

    def test_user_management_restricted_to_admin(self):
        """Non-admin users cannot access user management."""
        # Login as Sales Rep
        self.client.post('/login', data={'email': 'sales1@test.com', 'password': 'Sales@123'}, follow_redirects=True)
        res = self.client.get('/users/')
        self.assertEqual(res.status_code, 403)

        # Logout
        self.client.get('/logout', follow_redirects=True)

        # Login as Admin
        self.client.post('/login', data={'email': 'admin@test.com', 'password': 'Admin@123'}, follow_redirects=True)
        res_admin = self.client.get('/users/')
        self.assertEqual(res_admin.status_code, 200)
        self.assertIn(b'System Users', res_admin.data)

if __name__ == '__main__':
    unittest.main()
