import collections
import os

from django.conf import settings
from django.contrib import auth
from django.db import models, IntegrityError
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

class UserManager(auth.models.BaseUserManager):
    def create_user(self, nickname=None, password=None):
        if not nickname:
            nickname = self.make_default_nickname()

        done = False
        while not done:
            try:
                user = self.create(
                        id = self.make_user_id(),
                        nickname = nickname)
                done = True
            except IntegrityError:
                pass

        user.set_password(password)
        user.save(using=self._db)
        return user

    def make_user_id(self):
        a,b,c,d = os.urandom(4)
        a = ord(a)
        b = ord(b)
        c = ord(c)
        d = ord(d)
        a &= 0x7F
        return (a << 24) | (b << 16) | (c << 8) | d

    def make_default_nickname(self):
        return 'noname'

    def create_superuser(self, id, nickname, password):
        # The given id is ignored
        user = self.create_user(
                nickname = nickname,
                password = password
                )
        user.is_staff = True
        user.is_superuser = True
        user.is_registered = True
        user.save(using=self._db)
        return user

class User(auth.models.AbstractBaseUser, auth.models.PermissionsMixin):
    id = models.IntegerField(primary_key=True)
    nickname = models.CharField(max_length=128)
    primary_email = models.ForeignKey('UserEmail', db_index=False, null=True, related_name='+')
    date_joined = models.DateTimeField(_('date joined'), default=timezone.now)
    is_registered = models.BooleanField(default=False)

    is_staff = models.BooleanField(_('staff status'), default=False,
        help_text=_('Designates whether the user can log into this admin '
                    'site.'))

    is_active = models.BooleanField(_('active'), default=True,
        help_text=_('Designates whether this user should be treated as '
                    'active. Unselect this instead of deleting accounts.'))

    objects = UserManager()

    USERNAME_FIELD = 'id'
    REQUIRED_FIELDS = ['nickname']

    def __unicode__(self):
        return self.nickname

    def get_full_name(self):
        return self.nickname

    def get_short_name(self):
        return self.get_full_name()

class UserEmail(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, db_index=True)
    email = models.EmailField(unique=True)

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

class PhoneNumberManager(models.Manager):
    def authorize_phone_number(self, phone_number_str):
        try:
            phone_number = PhoneNumber.objects.get(phone_number=phone_number_str)
        except PhoneNumber.DoesNotExist:
            new_user = User.objects.create_user()
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
