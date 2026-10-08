import unittest
from datetime import datetime, timedelta
from app import create_app
from app.config import Config
from app.models import db, User, Role, AuditLog
from app.services.auth_service import AuthService

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False

class AuthTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_password_policy(self):
        """Tests password complexity requirements: min 8 chars, uppercase, lowercase, number, special char."""
        self.assertFalse(AuthService.validate_password_strength("short1!")[0])
        self.assertFalse(AuthService.validate_password_strength("nouppercase123!")[0])
        self.assertFalse(AuthService.validate_password_strength("NOLOWERCASE123!")[0])
        self.assertFalse(AuthService.validate_password_strength("NoNumberSpecial!")[0])
        self.assertFalse(AuthService.validate_password_strength("NoSpecialChar123")[0])
        
        is_valid, _ = AuthService.validate_password_strength("ValidPassword@123")
        self.assertTrue(is_valid)

    def test_user_creation_and_hashing(self):
        """Ensures passwords are never stored in plaintext."""
        user, msg = AuthService.create_user(
            name="Alice Wonder",
            email="alice@test.com",
            password="StrongPassword#2026",
            role=Role.SALES_EXECUTIVE
        )
        self.assertIsNotNone(user)
        self.assertNotEqual(user.password_hash, "StrongPassword#2026")
        self.assertTrue(user.check_password("StrongPassword#2026"))
        self.assertFalse(user.check_password("WrongPassword"))

    def test_login_flow(self):
        """Tests login with valid credentials and invalid credentials."""
        AuthService.create_user("Bob", "bob@test.com", "Password@123", Role.SALES_EXECUTIVE)

        # 1. Valid login
        res = self.client.post('/login', data={'email': 'bob@test.com', 'password': 'Password@123'}, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Bob', res.data)

        # Logout
        self.client.get('/logout', follow_redirects=True)

        # 2. Invalid login
        res_fail = self.client.post('/login', data={'email': 'bob@test.com', 'password': 'WrongPassword!'}, follow_redirects=True)
        self.assertIn(b'Invalid email or password', res_fail.data)

    def test_account_lockout_after_5_failed_attempts(self):
        """Tests lockout after 5 consecutive failed login attempts."""
        user, _ = AuthService.create_user("Charlie", "charlie@test.com", "Password@123", Role.SALES_EXECUTIVE)

        for attempt in range(1, 5):
            self.client.post('/login', data={'email': 'charlie@test.com', 'password': 'BadPassword@1'}, follow_redirects=True)
            u = User.query.filter_by(email="charlie@test.com").first()
            self.assertEqual(u.failed_login_count, attempt)
            self.assertFalse(u.is_locked_out)

        # 5th failed attempt triggers lockout
        self.client.post('/login', data={'email': 'charlie@test.com', 'password': 'BadPassword@1'}, follow_redirects=True)
        u_locked = User.query.filter_by(email="charlie@test.com").first()
        self.assertEqual(u_locked.failed_login_count, 5)
        self.assertTrue(u_locked.is_locked_out)

        # Subsequent login blocked due to lockout even with right password
        res = self.client.post('/login', data={'email': 'charlie@test.com', 'password': 'Password@123'}, follow_redirects=True)
        self.assertIn(b'Account is locked', res.data)

if __name__ == '__main__':
    unittest.main()
