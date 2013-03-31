import django.contrib.auth.backends

from phone_auth.models import User, UserEmail

class UserBackend(django.contrib.auth.backends.ModelBackend):
    def authenticate(self, username=None, password=None):
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
