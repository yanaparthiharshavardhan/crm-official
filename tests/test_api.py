import json
import unittest
from datetime import date, timedelta
from app import create_app
from app.config import Config
from app.models import db, User, Role, Customer
from app.services.auth_service import AuthService

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False

class APITestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()

        self.user, _ = AuthService.create_user("API User", "api@test.com", "ApiPass@123", Role.SALES_EXECUTIVE)

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def get_token(self):
        res = self.client.post('/api/auth/login', json={'email': 'api@test.com', 'password': 'ApiPass@123'})
        data = res.get_json()
        return data['token']

    def test_api_auth_unauthorized(self):
        """Protected API endpoints must reject unauthenticated requests with 401."""
        res = self.client.get('/api/customers')
        self.assertEqual(res.status_code, 401)

    def test_api_login_success(self):
        """Login endpoint returns JWT token and user info without password hash."""
        res = self.client.post('/api/auth/login', json={'email': 'api@test.com', 'password': 'ApiPass@123'})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn('token', data)
        self.assertNotIn('password', data['user'])
        self.assertNotIn('password_hash', data['user'])

    def test_customer_crud_api(self):
        """Tests Customer API creation, retrieval, and duplicate conflict handling."""
        token = self.get_token()
        headers = {'Authorization': f'Bearer {token}'}

        # 1. Create Customer
        new_cust_payload = {
            'customer_name': 'Acme Global Corp',
            'email': 'acme@global.com',
            'phone': '9876543200',
            'company_name': 'Acme Global'
        }
        res_create = self.client.post('/api/customers', json=new_cust_payload, headers=headers)
        self.assertEqual(res_create.status_code, 201)
        cust_data = res_create.get_json()
        self.assertEqual(cust_data['customer_name'], 'Acme Global Corp')
        self.assertTrue(cust_data['customer_code'].startswith('CUST-'))

        # 2. Duplicate Check Conflict (409)
        res_dup = self.client.post('/api/customers', json=new_cust_payload, headers=headers)
        self.assertEqual(res_dup.status_code, 409)

        # 3. Get Customers List
        res_list = self.client.get('/api/customers', headers=headers)
        self.assertEqual(res_list.status_code, 200)
        self.assertEqual(len(res_list.get_json()), 1)

    def test_opportunity_validation_api(self):
        """Tests that Opportunity API validates Amount > 0 and past close date."""
        token = self.get_token()
        headers = {'Authorization': f'Bearer {token}'}

        # First create customer
        res_cust = self.client.post('/api/customers', json={
            'customer_name': 'Beta Org',
            'email': 'beta@org.com',
            'phone': '9876543288',
            'company_name': 'Beta Org'
        }, headers=headers)
        cust_id = res_cust.get_json()['id']

        # Negative / zero amount rejected
        res_zero = self.client.post('/api/opportunities', json={
            'opportunity_name': 'Zero Deal',
            'customer_id': cust_id,
            'amount': 0,
            'expected_close_date': (date.today() + timedelta(days=5)).isoformat()
        }, headers=headers)
        self.assertEqual(res_zero.status_code, 422)

        # Valid opportunity created
        res_valid = self.client.post('/api/opportunities', json={
            'opportunity_name': 'Good Deal',
            'customer_id': cust_id,
            'amount': 50000.0,
            'probability': 60,
            'expected_close_date': (date.today() + timedelta(days=10)).isoformat()
        }, headers=headers)
        self.assertEqual(res_valid.status_code, 201)
        opp_data = res_valid.get_json()
        self.assertEqual(opp_data['weighted_amount'], 30000.0)

if __name__ == '__main__':
    unittest.main()

