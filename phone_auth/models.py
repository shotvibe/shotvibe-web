import collections
import random
from phone_auth.signals import user_avatar_changed
import re
import os
import string

import django.contrib.auth.models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.db import models, IntegrityError
from django.utils import crypto
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from analytics.event_tracking import track_event

from phone_auth.sms_send import is_test_number, send_sms

USER_AVATAR_DATA_REGEX = re.compile(r's3:.+?:user-avatar-\d+?-\d+?\.jpg')


def avatar_url_from_avatar_file_data(avatar_file):
    """Returns URL of the user's avatar image"""
    storage, bucket, filename = str(avatar_file).split(":")
    format_string = settings.AVATAR_STORAGE_URL_FORMAT_STRING_MAP.get(
        storage)

    if not format_string:
        return None

    return format_string.format(
        bucket_name=bucket,
        filename=filename
    )


def validate_avatar_file_data(value):
    """Validates value supplied for User.avatar_file attribute"""
    if not USER_AVATAR_DATA_REGEX.match(value):
        raise ValidationError("Wrong value for avatar file")


def random_default_avatar_file_data(*args, **kwargs):
    """Returns random default avatar_file location"""
    format_string, min_number, max_number = random.choice(
        settings.DEFAULT_AVATAR_FILES
    )
    return format_string.format(random.randint(min_number, max_number))


class UserManager(django.contrib.auth.models.BaseUserManager):
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

class User(django.contrib.auth.models.AbstractBaseUser, django.contrib.auth.models.PermissionsMixin):
    STATUS_JOINED = 'joined'
    STATUS_SMS_SENT = 'sms_sent'
    STATUS_INVITATION_VIEWED = 'invitation_viewed'

    id = models.IntegerField(primary_key=True)
    nickname = models.CharField(max_length=128)
    primary_email = models.ForeignKey('UserEmail', db_index=False, null=True, blank=True, related_name='+', on_delete=models.SET_NULL)
    date_joined = models.DateTimeField(_('date joined'), default=timezone.now)
    # TODO This doesn't seem to be used, probably should delete it
    is_registered = models.BooleanField(default=False)

    is_staff = models.BooleanField(_('staff status'), default=False,
                                   help_text=_('Designates whether the user '
                                               'can log into this admin site.'))

    is_active = models.BooleanField(
        _('active'),
        default=True,
        help_text=_('Designates whether this user should be treated as active. '
                    'Unselect this instead of deleting accounts.')
    )

    last_online = models.DateTimeField(default=timezone.now)

    avatar_file = models.CharField(max_length=128,
                                   validators=[validate_avatar_file_data],
                                   default=random_default_avatar_file_data)

    user_glance_score = models.IntegerField(default=25)

    # hidden_photos = models.CharField(default='{}',)

    objects = UserManager()

    USERNAME_FIELD = 'id'
    REQUIRED_FIELDS = ['nickname']

    def __unicode__(self):
        return u'{0} ({1})'.format(self.id, self.nickname)

    def save(self, *args, **kwargs):
        # When creating a new user from the Django admin, there will be no id
        # set, so we handle it here
        if not self.id:
            new_user = User.objects.create_user()
            # Copy the id from the newly created user to the current user
            # object. This will cause the current User object to "save over"
            # the new_user object
            self.id = new_user.id

        super(User, self).save(*args, **kwargs)

    def get_invite_status(self):
        query = self.phonenumber_set.filter(verified=True)
        if query.count() > 0:
            return User.STATUS_JOINED
        else:
            query = PhoneNumberLinkCode.objects.filter(
                phone_number__in=self.phonenumber_set.all())
            for link_code in query:
                if link_code.was_visited:
                    return User.STATUS_INVITATION_VIEWED
            return User.STATUS_SMS_SENT

    def get_full_name(self):
        return self.nickname

    def get_short_name(self):
        return self.get_full_name()

    def get_avatar_url(self):
        """Returns URL of the user's avatar image"""
        return avatar_url_from_avatar_file_data(self.avatar_file)

    def get_primary_phone_number(self):
        return PhoneNumber.objects.filter(user=self).order_by('date_created').first()

    def pick_anonymous_avatar(self, phone_number_str, save=False):
        """Picks up avatar used for anonymous contact data for the given
        phone_number_str.

        If there is no AnonymousPhoneNumber for the given phone number
         it does nothing.
        Save self if `save` is True.
        """
        try:
            apn = AnonymousPhoneNumber.objects.only('avatar_file').\
                get(phone_number=phone_number_str)
        except AnonymousPhoneNumber.DoesNotExist:
            pass
        else:
            self.avatar_file = apn.avatar_file
            if save:
                self.save()

    def increment_user_glance_score(self, delta):
        User.objects.filter(id=self.id).update(user_glance_score=models.F('user_glance_score') + delta)
        updated_glance_score = User.objects.get(pk=self.id).user_glance_score

        from photos_api import device_push
        device_push.broadcast_user_glance_score_update(self.id, updated_glance_score)

    def set_last_online(self, now):
        User.objects.filter(pk=self.id).update(last_online=now)


class UserGlanceScoreSnapshotManager(models.Manager):
    def take_snapshot(self, current_time):
        for user in User.objects.all():
            UserGlanceScoreSnapshot.objects.create(
                user = user,
                user_glance_score = user.user_glance_score,
                snap_date = current_time
            )

    def get_closest_snapshot(self, date):
        snap = UserGlanceScoreSnapshot.objects.filter(snap_date__gte=date)[0]
        return snap.snap_date

    def get_score_delta(self, start_date):
        start_snaps = UserGlanceScoreSnapshot.objects.filter(snap_date=start_date)
        start_snaps_dict = {}
        for s in start_snaps:
            start_snaps_dict[s.user.id] = s.user_glance_score

        results = []
        for user in User.objects.all():
            start_score = start_snaps_dict.get(user.id, 0)
            score_delta = user.user_glance_score - start_score
            results.append({
                'user': user,
                'score_delta': score_delta
            })

        results.sort(key=lambda result: result['score_delta'])
        results.reverse()

        return results


class UserGlanceScoreSnapshot(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, db_index=True)
    user_glance_score = models.IntegerField()
    snap_date = models.DateTimeField(db_index=True)

    objects = UserGlanceScoreSnapshotManager()


class UserEmail(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, db_index=True)
    email = models.EmailField(unique=True)

    def save(self, *args, **kwargs):
        result = super(UserEmail, self).save(*args, **kwargs)
        if not self.user.primary_email:
            self.user.primary_email = self
            self.user.save(update_fields=['primary_email'])
        return result

    def __unicode__(self):
        return self.email

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

    def logout(self):
        self.delete()

class PhoneNumberManager(models.Manager):
    def authorize_phone_number(self, phone_number_str):
        try:
            phone_number = PhoneNumber.objects.get(phone_number=phone_number_str)
        except PhoneNumber.DoesNotExist:
            new_user = User.objects.create_user()
            phone_number = self.create(
                phone_number=phone_number_str,
                user=new_user,
                date_created=timezone.now(),
                verified=False
            )
            new_user.pick_anonymous_avatar(phone_number_str)
            new_user.save()

            user_avatar_changed.send(sender=self, user=new_user)

        confirmation_key = generate_key()
        if is_test_number(phone_number.phone_number):
            confirmation_code = '6666'
        else:
            confirmation_code = crypto.get_random_string(4, string.digits)

        PhoneNumberConfirmSMSCode.objects.get_or_create(
                phone_number = phone_number,
                confirmation_key = confirmation_key,
                confirmation_code = confirmation_code,
                date_created = timezone.now()
                )
        if not settings.DEBUG:
            send_sms(phone_number.phone_number, 'Your Glance Verification Code: ' + confirmation_code)

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

        # Confirmation successful

        user = confirm_obj.phone_number.user

        if not confirm_obj.phone_number.verified:
            confirm_obj.phone_number.verified = True
            confirm_obj.phone_number.save(update_fields=['verified'])

            from welcome_album.models import ScheduledWelcomeAlbumJob
            ScheduledWelcomeAlbumJob.objects.schedule_job(user, timezone.now())

        auth_token = AuthToken.objects.create_auth_token(user, device_description, timezone.now())

        # TODO maybe confirm_obj.delete(), or maybe better to wait for it to be
        # garbage collected automatically

        # TODO Also maybe delete a PhoneNumberLinkCode if it exists for this phone_number

        result.success = True
        result.user = user
        result.auth_token = auth_token.key
        return result

    def get_or_create_phone_number(self, phone_number_str, default_nickname, current_time):
        """
        phone_number_str: Must be formatted as international E164

        default_nickname: If the phone number isn't found (doesn't belong to
        any existing users) then a new user will be created, with nickname set
        to `default_nickname'

        Returns a tuple of (phone_number, created) where `phone_number' is a
        PhoneNumber object, and `created' is a boolean that indicates if a new
        phone number (and associated new user) was created
        """

        tmp_user = User.objects.create_user(nickname=default_nickname)
        delete_tmp_user = True
        try:
            phone_number, created = PhoneNumber.objects.get_or_create(phone_number=phone_number_str, defaults={
                    'user' : tmp_user,
                    'date_created' : current_time,
                    'verified' : False
                    })
            if created:
                delete_tmp_user = False
            return phone_number, created
        finally:
            if delete_tmp_user:
                tmp_user.delete()


class AnonymousPhoneNumber(models.Model):
    phone_number = models.CharField(max_length=32, unique=True, db_index=True)
    date_created = models.DateTimeField(default=timezone.now)
    avatar_file = models.CharField(max_length=128,
                                   validators=[validate_avatar_file_data],
                                   default=random_default_avatar_file_data)
    is_mobile = models.BooleanField()
    is_mobile_queried = models.DateTimeField()

    def get_avatar_url(self):
        return avatar_url_from_avatar_file_data(self.avatar_file)

    def __unicode__(self):
        return self.phone_number


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

    def __unicode__(self):
        return self.confirmation_key + ': ' + unicode(self.phone_number.phone_number)

class PhoneNumberLinkCodeManager(models.Manager):
    # TODO Should throw an exception if sending the SMS fails (because of invalid phone number)
    def invite_phone_number(self, inviter, phone_number_str, nickname, date_invited, sms_message_formatter, sms_analytics_event_name, sms_analytics_event_properties):
        """
        phone_number_str: Must be formatted as international E164

        Returns the user
        """
        try:
            phone_number = PhoneNumber.objects.get(phone_number=phone_number_str)

            if phone_number.verified:
                return phone_number.user
        except PhoneNumber.DoesNotExist:
            new_user = User.objects.create_user(nickname=nickname)
            phone_number = PhoneNumber.objects.create(
                    phone_number = phone_number_str,
                    user = new_user,
                    date_created = date_invited,
                    verified = False)
            new_user.pick_anonymous_avatar(phone_number_str)
            new_user.save()

            user_avatar_changed.send(sender=self, user=new_user)

        link_code_object, created = PhoneNumberLinkCode.objects.get_or_create(phone_number=phone_number, defaults={
            'invite_code': PhoneNumberLinkCode.generate_invite_code(),
            'inviting_user': inviter,
            'date_created': date_invited,
            'was_visited': False
            })

        inviter_phone = inviter.get_primary_phone_number()
        if inviter_phone:
            sender_phone = inviter_phone.phone_number
        else:
            sender_phone = None

        message = sms_message_formatter(link_code_object)

        invite_url_prefix = 'https://i.useglance.com'
        send_sms(phone_number.phone_number, message + '\n' + link_code_object.get_invite_page(invite_url_prefix), sender_phone)

        track_event(link_code_object.phone_number.user, sms_analytics_event_name, sms_analytics_event_properties)

        return link_code_object.phone_number.user


class PhoneNumberLinkCode(models.Model):
    invite_code = models.CharField(max_length=32, primary_key=True)
    phone_number = models.ForeignKey(PhoneNumber, unique=True)
    inviting_user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='+')
    date_created = models.DateTimeField(db_index=True)
    was_visited = models.BooleanField(default=False)

    objects = PhoneNumberLinkCodeManager()

    @staticmethod
    def generate_invite_code():
        return crypto.get_random_string(16, string.ascii_letters + string.digits)

    def __unicode__(self):
        value = self.invite_code + ': ' + unicode(self.phone_number)
        if self.was_visited:
            value += ' (visited)'
        else:
            value += ' (not visited)'
        return value

    def get_invite_page(self, url_prefix=None):
        import frontend.urls
        from frontend.mobile_views import invite_page

        if not url_prefix:
            url_prefix = ''
        return url_prefix + reverse(invite_page, urlconf=frontend.urls, args=(self.invite_code,))


class PhoneContact(models.Model):
    """Phone contact data uploaded by users to see who from his
    address book is registered at Shotvibe"""
    anonymous_phone_number = models.ForeignKey(AnonymousPhoneNumber)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, blank=True, null=True,
                             default=None, related_name="phone_contacts")
    created_by_user = models.ForeignKey(settings.AUTH_USER_MODEL,
                                        related_name="created_phone_contacts")
    date_created = models.DateTimeField(default=timezone.now)
    contact_nickname = models.TextField()


def update_anonymous_phone_number_avatar(sender, **kwargs):
    user = kwargs.get('user')
    query = user.phone_contacts.all().select_related('anonymous_phone_number')\
        .only('anonymous_phone_number')
    for phone_contact in query:
        if phone_contact.anonymous_phone_number.avatar_file != user.avatar_file:
            phone_contact.anonymous_phone_number.avatar_file = user.avatar_file
            phone_contact.anonymous_phone_number.save()

user_avatar_changed.connect(update_anonymous_phone_number_avatar)
