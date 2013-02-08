import collections
import os

from django.conf import settings
from django.contrib import auth
from django.db import models
from django.utils import timezone

class AuthTokenManager(models.Manager):
    def get(self, *args, **kwargs):
        result = super(AuthTokenManager, self).get(*args, **kwargs)
        result.last_access = timezone.now()
        result.save(update_fields=['last_access'])
        return result

    def create_auth_token(self, user, description, date_created):
        token = self.create(
                key = generate_key(),
                description = description,
                user = user,
                date_created = date_created,
                last_access = date_created
                )
        return token

def generate_key():
    return ''.join(["{0:02x}".format(ord(c)) for c in os.urandom(20)])

class AuthToken(models.Model):
    key = models.CharField(max_length=40, primary_key=True)
    description = models.TextField()
    user = models.ForeignKey(settings.AUTH_USER_MODEL, db_index=True)
    date_created = models.DateTimeField()
    last_access = models.DateTimeField()
    last_access_ip = models.GenericIPAddressField(null=True, blank=True)

    objects = AuthTokenManager()

    def __unicode__(self):
        return unicode(self.user) + ': ' + self.description

def create_new_user():
    random_username = str(int(os.urandom(5).encode('hex'), 16))
    # TODO Handle username collision and retry
    user = auth.get_user_model().objects.create_user(random_username)
    return user

class PhoneNumberManager(models.Manager):
    def authorize_phone_number(self, phone_number_str):
        try:
            phone_number = PhoneNumber.objects.get(phone_number=phone_number_str)
        except PhoneNumber.DoesNotExist:
            new_user = create_new_user()
            phone_number = self.create(
                    phone_number = phone_number_str,
                    user = new_user,
                    date_created = timezone.now(),
                    verified = False)

        confirmation_key = generate_key()
        confirmation_code = '6666' # TODO Temporary!

        PhoneNumberConfirmSMSCode.objects.get_or_create(
                phone_number = phone_number,
                confirmation_key = confirmation_key,
                confirmation_code = confirmation_code,
                date_created = timezone.now()
                )

        # TODO Send SMS code to phone

        return confirmation_key

    def confirm_phone_number(self, confirmation_key, confirmation_code, device_description):
        result = collections.namedtuple('ConfirmResult', ['success', 'user', 'auth_token', 'expired_key', 'incorrect_code'])
        try:
            confirm_obj = PhoneNumberConfirmSMSCode.objects.get(confirmation_key=confirmation_key)
        except PhoneNumberConfirmSMSCode.DoesNotExist:
            result.success = False
            result.incorrect_code = False
            result.expired_key = True
            return result

        # TODO Verify that the confirm_obj isn't stale

        if confirmation_code != confirm_obj.confirmation_code:
            result.success = False
            result.expired_key = False
            result.incorrect_code = True
            return result

        user = confirm_obj.phone_number.user

        auth_token = AuthToken.objects.create_auth_token(user, device_description, timezone.now())

        # TODO maybe confirm_obj.delete(), or maybe better to wait for it to be
        # garbage collected automatically

        result.success = True
        result.user = user
        result.auth_token = auth_token.key
        return result

class PhoneNumber(models.Model):
    phone_number = models.CharField(max_length=32, unique=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL)
    date_created = models.DateTimeField(db_index=True)
    verified = models.BooleanField()

    objects = PhoneNumberManager()

    def __unicode__(self):
        return self.phone_number

# This table should be periodically garbage collected. Old rows should be
# deleted.
class PhoneNumberConfirmSMSCode(models.Model):
    confirmation_key = models.CharField(max_length=40, primary_key=True)
    confirmation_code = models.CharField(max_length=6)
    phone_number = models.ForeignKey(PhoneNumber)
    date_created = models.DateTimeField(db_index=True)

#class PhoneNumberLinkCode(models.Model):
#    link_code = models.CharField(max_length=12, primary_key=True)
#    user = models.ForeignKey(settings.AUTH_USER_MODEL, unique=True)
