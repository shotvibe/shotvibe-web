from django.contrib.auth.backends import ModelBackend
from phone_auth.models import User, UserEmail


class UserBackend(ModelBackend):
    def authenticate(self, username=None, password=None, **kwargs):
        if '@' in username:
            try:
                user_email = UserEmail.objects.get(email=username)
            except UserEmail.DoesNotExist:
                return None
            user = user_email.user
        elif '+' in username:
            # TODO Authenticate phone number ...
            return None
        else:
            try:
                i = int(username)
            except ValueError:
                return None
            try:
                user = User.objects.get(id=i)
            except User.DoesNotExist:
                return None

        if user.check_password(password):
            return user
        else:
            return None
