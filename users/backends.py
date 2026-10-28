from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class EmailBackend(ModelBackend):
    """Authenticate with a case-insensitive email address and a password.

    Django's `authenticate()` passes credentials as keyword arguments. We accept
    `email=` (used by the API) and also `username=` (used by the admin login
    form, which posts the USERNAME_FIELD under that name).
    """

    def authenticate(self, request, email=None, password=None, username=None, **kwargs):
        User = get_user_model()
        identifier = email or username
        if not identifier or not password:
            return None
        try:
            user = User.objects.get(email__iexact=identifier.strip())
        except User.DoesNotExist:
            # Run the hasher once to reduce timing differences between
            # "unknown email" and "wrong password".
            User().set_password(password)
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
