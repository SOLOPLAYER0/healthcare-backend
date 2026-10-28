from django.contrib.auth import get_user_model
from rest_framework.test import APIClient, APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from config.testing import PASSWORD, make_user

User = get_user_model()

REGISTER_URL = "/api/auth/register/"
LOGIN_URL = "/api/auth/login/"
REFRESH_URL = "/api/auth/token/refresh/"
PROTECTED_URL = "/api/patients/"


class RegisterTests(APITestCase):
    def valid_data(self, **overrides):
        data = {"name": "Alice", "email": "alice@example.com", "password": PASSWORD}
        data.update(overrides)
        return data

    def test_register_success(self):
        response = self.client.post(REGISTER_URL, self.valid_data())
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["user"]["email"], "alice@example.com")
        self.assertEqual(response.data["user"]["name"], "Alice")

    def test_response_does_not_expose_password(self):
        response = self.client.post(REGISTER_URL, self.valid_data())
        self.assertNotIn("password", response.data["user"])
        self.assertNotIn(PASSWORD, response.content.decode())

    def test_password_is_hashed_in_database(self):
        self.client.post(REGISTER_URL, self.valid_data())
        user = User.objects.get(email="alice@example.com")
        self.assertNotEqual(user.password, PASSWORD)
        self.assertTrue(user.password.startswith("pbkdf2_"))
        self.assertTrue(user.check_password(PASSWORD))

    def test_email_is_stored_lowercase(self):
        self.client.post(REGISTER_URL, self.valid_data(email="Alice@Example.COM"))
        self.assertTrue(User.objects.filter(email="alice@example.com").exists())

    def test_duplicate_email_rejected(self):
        self.client.post(REGISTER_URL, self.valid_data())
        response = self.client.post(REGISTER_URL, self.valid_data(name="Other"))
        self.assertEqual(response.status_code, 400)
        self.assertIn("email", response.data["errors"])
        self.assertEqual(User.objects.count(), 1)

    def test_duplicate_email_is_case_insensitive(self):
        self.client.post(REGISTER_URL, self.valid_data())
        response = self.client.post(REGISTER_URL, self.valid_data(email="ALICE@example.com"))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(User.objects.count(), 1)

    def test_invalid_email_rejected(self):
        response = self.client.post(REGISTER_URL, self.valid_data(email="not-an-email"))
        self.assertEqual(response.status_code, 400)
        self.assertIn("email", response.data["errors"])

    def test_missing_fields_rejected(self):
        response = self.client.post(REGISTER_URL, {})
        self.assertEqual(response.status_code, 400)
        for field in ("name", "email", "password"):
            self.assertIn(field, response.data["errors"])

    def test_blank_name_rejected(self):
        response = self.client.post(REGISTER_URL, self.valid_data(name="   "))
        self.assertEqual(response.status_code, 400)
        self.assertIn("name", response.data["errors"])

    def test_weak_password_rejected(self):
        response = self.client.post(REGISTER_URL, self.valid_data(password="12345678"))
        self.assertEqual(response.status_code, 400)
        self.assertIn("password", response.data["errors"])

    def test_short_password_rejected(self):
        response = self.client.post(REGISTER_URL, self.valid_data(password="Ab1#"))
        self.assertEqual(response.status_code, 400)
        self.assertIn("password", response.data["errors"])

    def test_register_does_not_require_authentication(self):
        # Even a bogus Authorization header must not block registration.
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION="Bearer garbage")
        response = client.post(REGISTER_URL, self.valid_data())
        self.assertEqual(response.status_code, 201)


class LoginTests(APITestCase):
    def setUp(self):
        self.user = make_user("alice@example.com", "Alice")

    def test_login_success_returns_tokens(self):
        response = self.client.post(
            LOGIN_URL, {"email": "alice@example.com", "password": PASSWORD}
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertEqual(response.data["user"]["email"], "alice@example.com")
        self.assertNotIn("password", response.data["user"])

    def test_login_email_is_case_insensitive(self):
        response = self.client.post(
            LOGIN_URL, {"email": "ALICE@Example.com", "password": PASSWORD}
        )
        self.assertEqual(response.status_code, 200)

    def test_wrong_password(self):
        response = self.client.post(
            LOGIN_URL, {"email": "alice@example.com", "password": "WrongPass#1"}
        )
        self.assertEqual(response.status_code, 401)
        self.assertFalse(response.data["success"])
        self.assertEqual(response.data["message"], "Invalid email or password.")

    def test_unknown_email_gives_same_error_as_wrong_password(self):
        wrong_pw = self.client.post(
            LOGIN_URL, {"email": "alice@example.com", "password": "WrongPass#1"}
        )
        unknown = self.client.post(
            LOGIN_URL, {"email": "nobody@example.com", "password": PASSWORD}
        )
        self.assertEqual(unknown.status_code, 401)
        self.assertEqual(unknown.data, wrong_pw.data)

    def test_inactive_user_cannot_log_in(self):
        self.user.is_active = False
        self.user.save()
        response = self.client.post(
            LOGIN_URL, {"email": "alice@example.com", "password": PASSWORD}
        )
        self.assertEqual(response.status_code, 401)

    def test_missing_fields(self):
        response = self.client.post(LOGIN_URL, {})
        self.assertEqual(response.status_code, 400)
        self.assertIn("email", response.data["errors"])
        self.assertIn("password", response.data["errors"])

    def test_invalid_email_format(self):
        response = self.client.post(LOGIN_URL, {"email": "bad", "password": PASSWORD})
        self.assertEqual(response.status_code, 400)

    def test_refresh_token_returns_new_access_token(self):
        login = self.client.post(
            LOGIN_URL, {"email": "alice@example.com", "password": PASSWORD}
        )
        response = self.client.post(REFRESH_URL, {"refresh": login.data["refresh"]})
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)

    def test_invalid_refresh_token(self):
        response = self.client.post(REFRESH_URL, {"refresh": "nonsense"})
        self.assertEqual(response.status_code, 401)


class JWTAuthenticationTests(APITestCase):
    """The real JWT flow protects endpoints (no mock auth)."""

    def setUp(self):
        self.user = make_user()

    def test_no_token_returns_401(self):
        response = self.client.get(PROTECTED_URL)
        self.assertEqual(response.status_code, 401)
        self.assertFalse(response.data["success"])

    def test_invalid_token_returns_401(self):
        self.client.credentials(HTTP_AUTHORIZATION="Bearer not.a.token")
        response = self.client.get(PROTECTED_URL)
        self.assertEqual(response.status_code, 401)

    def test_wrong_auth_scheme_returns_401(self):
        login = self.client.post(
            LOGIN_URL, {"email": "alice@example.com", "password": PASSWORD}
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {login.data['access']}")
        response = self.client.get(PROTECTED_URL)
        self.assertEqual(response.status_code, 401)

    def test_valid_access_token_works(self):
        login = self.client.post(
            LOGIN_URL, {"email": "alice@example.com", "password": PASSWORD}
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
        response = self.client.get(PROTECTED_URL)
        self.assertEqual(response.status_code, 200)

    def test_refresh_token_cannot_be_used_as_access_token(self):
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh}")
        response = self.client.get(PROTECTED_URL)
        self.assertEqual(response.status_code, 401)

    def test_token_for_deleted_user_is_rejected(self):
        login = self.client.post(
            LOGIN_URL, {"email": "alice@example.com", "password": PASSWORD}
        )
        self.user.delete()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
        response = self.client.get(PROTECTED_URL)
        self.assertEqual(response.status_code, 401)

    def test_error_responses_do_not_leak_internals(self):
        self.client.credentials(HTTP_AUTHORIZATION="Bearer not.a.token")
        body = self.client.get(PROTECTED_URL).content.decode()
        self.assertNotIn("Traceback", body)
        self.assertNotIn("psycopg", body)
