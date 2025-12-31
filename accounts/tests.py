# auth_app/tests.py
from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse


class RegistrationTests(TestCase):
    """Test user registration functionality"""

    def setUp(self):
        self.client = Client()
        self.register_url = reverse("register")
        self.login_url = reverse("login")

    def test_register_page_loads(self):
        """Registration page should load successfully"""
        response = self.client.get(self.register_url)
        if response.status_code == 301:
            print(f"DEBUG: 301 Redirect to: {response.url}")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Register")

    def test_register_with_valid_data(self):
        """User should be created with valid registration data"""
        response = self.client.post(
            self.register_url,
            {
                "username": "newuser",
                "first_name": "New",
                "last_name": "User",
                "email": "newuser@example.com",
                "phone_number": "08031234567",
                "password": "securepass123",
                "password_confirm": "securepass123",
            },
        )

        # Should redirect after successful registration
        self.assertEqual(response.status_code, 302)

        # User should exist in database
        self.assertTrue(User.objects.filter(username="newuser").exists())

        # Should be able to login with new credentials
        user_exists = self.client.login(username="newuser", password="securepass123")
        self.assertTrue(user_exists)

    def test_register_with_mismatched_passwords(self):
        """Registration should fail when passwords don't match"""
        response = self.client.post(
            self.register_url,
            {
                "username": "newuser",
                "first_name": "New",
                "last_name": "User",
                "email": "newuser@example.com",
                "phone_number": "08031234567",
                "password": "password123",
                "password_confirm": "differentpassword",
            },
        )

        # Should stay on registration page
        self.assertEqual(response.status_code, 200)

        # User should NOT be created
        self.assertFalse(User.objects.filter(username="newuser").exists())

    def test_register_with_existing_username(self):
        """Registration should fail with duplicate username"""
        # Create existing user
        User.objects.create_user(username="existinguser", password="pass123")

        response = self.client.post(
            self.register_url,
            {
                "username": "existinguser",
                "first_name": "Existing",
                "last_name": "User",
                "email": "existing@example.com",
                "phone_number": "08031234567",
                "password": "newpass123",
                "password_confirm": "newpass123",
            },
        )

        # Should stay on registration page
        self.assertEqual(response.status_code, 200)

        # Should only have one user with this username
        self.assertEqual(User.objects.filter(username="existinguser").count(), 1)

    def test_register_with_empty_fields(self):
        """Registration should fail with empty fields"""
        response = self.client.post(
            self.register_url,
            {
                "username": "",
                "password": "",
                "password_confirm": "",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.count(), 0)


class LoginTests(TestCase):
    """Test user login functionality"""

    def setUp(self):
        self.client = Client()
        self.login_url = reverse("login")
        self.home_url = reverse("dashboard")

        # Create test user
        self.user = User.objects.create_user(username="testuser", password="testpass123")

    def test_login_page_loads(self):
        """Login page should load successfully"""
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Login")

    def test_login_with_valid_credentials(self):
        """User should login successfully with correct credentials"""
        response = self.client.post(
            self.login_url, {"username": "testuser", "password": "testpass123"}
        )

        # Should redirect after successful login
        self.assertEqual(response.status_code, 302)

        # User should be authenticated
        user = response.wsgi_request.user
        self.assertTrue(user.is_authenticated)

    def test_login_with_wrong_password(self):
        """Login should fail with incorrect password"""
        response = self.client.post(
            self.login_url, {"username": "testuser", "password": "wrongpassword"}
        )

        # Should stay on login page
        self.assertEqual(response.status_code, 200)

        # Should show error message (check your actual error text)
        content = response.content.decode("utf-8").lower()
        self.assertTrue("error" in content or "invalid" in content)

    def test_login_with_nonexistent_user(self):
        """Login should fail with non-existent username"""
        response = self.client.post(
            self.login_url, {"username": "nonexistent", "password": "anypassword"}
        )

        self.assertEqual(response.status_code, 200)
        # Should show error message
        content = response.content.decode("utf-8").lower()
        self.assertTrue("error" in content or "invalid" in content)

    def test_login_with_empty_fields(self):
        """Login should fail with empty fields"""
        response = self.client.post(self.login_url, {"username": "", "password": ""})

        self.assertEqual(response.status_code, 200)


class LogoutTests(TestCase):
    """Test user logout functionality"""

    def setUp(self):
        self.client = Client()
        self.logout_url = reverse("logout")
        self.login_url = reverse("login")

        # Create and login user
        self.user = User.objects.create_user(username="testuser", password="testpass123")
        self.client.login(username="testuser", password="testpass123")

    def test_logout_page_loads(self):
        """Logout confirmation page should load for authenticated users"""
        response = self.client.get(self.logout_url)

        # If your logout view redirects immediately, this will be 302
        # If it shows a confirmation page, this will be 200
        self.assertIn(response.status_code, [200, 302])

        if response.status_code == 200:
            self.assertContains(response, "Logout")

    def test_logout_functionality(self):
        """User should be logged out after POST to logout"""
        response = self.client.post(self.logout_url)

        # Should redirect after logout
        self.assertEqual(response.status_code, 302)

        # User should no longer be authenticated
        response = self.client.get(self.login_url)
        self.assertNotIn("_auth_user_id", self.client.session)


class ProtectedPageTests(TestCase):
    """Test protected page access control"""

    def setUp(self):
        self.client = Client()
        self.protected_url = reverse("profile")
        self.login_url = reverse("login")

        # Create test user
        self.user = User.objects.create_user(username="testuser", password="testpass123")

    def test_protected_page_requires_login(self):
        """Protected page should redirect to login for anonymous users"""
        response = self.client.get(self.protected_url)

        # Should redirect
        self.assertEqual(response.status_code, 302)

        # Should redirect to login page
        self.assertIn("login", response.url)

    def test_protected_page_accessible_when_logged_in(self):
        """Protected page should be accessible for authenticated users"""
        # Login first
        self.client.login(username="testuser", password="testpass123")

        response = self.client.get(self.protected_url)

        # Should load successfully
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Profile")

    def test_protected_page_after_logout(self):
        """Protected page should not be accessible after logout"""
        # Login
        self.client.login(username="testuser", password="testpass123")

        # Logout
        self.client.post(reverse("logout"))

        # Try to access protected page
        response = self.client.get(self.protected_url)

        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url)


class AuthenticationFlowTests(TestCase):
    """Test complete authentication workflows"""

    def setUp(self):
        self.client = Client()
        self.register_url = reverse("register")
        self.login_url = reverse("login")
        self.protected_url = reverse("profile")
        self.logout_url = reverse("logout")

    def test_complete_registration_and_login_flow(self):
        """Test full flow: register -> login -> access protected page"""
        # Step 1: Register
        response = self.client.post(
            self.register_url,
            {
                "username": "flowuser",
                "first_name": "Flow",
                "last_name": "User",
                "email": "flowuser@example.com",
                "phone_number": "08031234567",
                "password": "flowpass123",
                "password_confirm": "flowpass123",
            },
        )
        self.assertEqual(response.status_code, 302)

        # Step 2: Login
        response = self.client.post(
            self.login_url, {"username": "flowuser", "password": "flowpass123"}
        )
        self.assertEqual(response.status_code, 302)

        # Step 3: Access protected page
        response = self.client.get(self.protected_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Profile")

    def test_complete_logout_flow(self):
        """Test full flow: login -> access protected -> logout -> cannot access"""
        # Create user
        User.objects.create_user(username="logoutuser", password="pass123")

        # Login
        self.client.login(username="logoutuser", password="pass123")

        # Access protected page (should work)
        response = self.client.get(self.protected_url)
        self.assertEqual(response.status_code, 200)

        # Logout
        self.client.post(self.logout_url)

        # Try protected page again (should redirect)
        response = self.client.get(self.protected_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url)
