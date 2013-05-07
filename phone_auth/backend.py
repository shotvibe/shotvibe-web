import django.contrib.auth.backends

import phonenumbers

from phone_auth.models import User, UserEmail, PhoneNumber

class UserBackend(django.contrib.auth.backends.ModelBackend):
    def authenticate(self, username=None, password=None):
        if '@' in username:
            try:
                user_email = UserEmail.objects.get(email=username)
            except UserEmail.DoesNotExist:
                return None
            user = user_email.user
        elif '+' in username:
            number = phonenumbers.parse(username, None)
            canonical_number = phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.E164)
            try:
                user_phone_number = PhoneNumber.objects.get(phone_number=canonical_number)
            except PhoneNumber.DoesNotExist:
                return None
            user = user_phone_number.user
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
