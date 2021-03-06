import re
import string
import phonenumbers
from operator import methodcaller
from phonenumbers.phonenumberutil import NumberParseException

from django.db import models, transaction, IntegrityError
from django.conf import settings
from django.core.urlresolvers import reverse
from django.utils import timezone
import django.db

from phone_auth.models import PhoneNumber, PhoneNumberLinkCode
from photos.models import Album
from photos import photo_operations


class Organization(models.Model):
    code = models.CharField(max_length=128)

    def __unicode__(self):
        return self.code

    def add_user(self, user):
        organizationUser = OrganizationUser(
            organization=self,
            user=user,
        )
        self.organizationuser_set.add(organizationUser)

    def is_member(self, user):
        n = self.organizationuser_set.filter(user=user).count()
        return n == 1

    def create_event(self, event, user):
        with transaction.atomic():
            album = Album.objects.create_album(
                creator=user,
                name=event.name,
            )
            album.save()
            event.created_by = user
            event.organization = self
            event.album = album
            event.save()
        return event


class OrganizationUser(models.Model):
    organization = models.ForeignKey(Organization)
    user = models.ForeignKey(settings.AUTH_USER_MODEL)

    class Meta:
        unique_together = ('organization', 'user')


class EventManager(models.Manager):
    def handle_event_registration_payload(self, user, payload_id):
        from photos_api.serializers import MemberIdentifier
        try:
            event = Event.objects.get(pk=int(payload_id))
        except (ValueError, TypeError, Event.DoesNotExist):
            # payload was bad, perhaps log this somewhere?
            pass
        else:
            eventAlbum = event.album
            inviter = event.created_by
            eventAlbum.add_members(inviter, [MemberIdentifier(user_id=user.id)], timezone.now(), Album.default_sms_message_formatter)

    def handle_partner_registration_payload(self, user, partner_id):
        if partner_id == 'mazaltov':
            # Hard-coded album id that is used as a template
            MAZALTOV_ALBUM_ID = 2811

            mazaltov_album = Album.objects.get(pk=MAZALTOV_ALBUM_ID)
            photo_ids = [p.photo_id for p in mazaltov_album.get_photos()]

            now = timezone.now()

            class CreateAlbumAction(photo_operations.ExThread):
                def run_with_exception(self):
                    try:
                        self.perform_action()
                    finally:
                        django.db.close_old_connections()

                def perform_action(self):
                    with transaction.atomic():
                        self.new_album = Album.objects.create_album(mazaltov_album.creator, mazaltov_album.name, now)
                        with self.new_album.modify(now) as m:
                            m.add_user_id(mazaltov_album.creator, user.id)

            action = CreateAlbumAction()
            # TODO This is only current needed to make tests work with sqlite
            # See this bug:
            #     https://code.djangoproject.com/ticket/12118
            if settings.USING_LOCAL_PHOTOS:
                action.perform_action()
            else:
                action.daemon = False
                action.start()
                action.join_with_exception()

            photo_operations.copy_photos_to_album(mazaltov_album.creator, photo_ids, action.new_album.id, now)


class Event(models.Model):
    organization = models.ForeignKey(Organization)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL)
    album = models.ForeignKey(Album)
    name = models.CharField(max_length=255)
    time = models.DateTimeField()
    sms_message = models.TextField(
        help_text="Hey ${name}, somebody invited you to an event")
    push_notification = models.CharField(max_length=255)
    location = models.CharField(max_length=255)
    #logo =
    #banner
    html_content = models.TextField(blank=True)
    app_button_custom_text = models.CharField(max_length=255, blank=True)

    objects = EventManager()

    def create_link(self, slug=None):
        if slug:
            if EventLink.objects.filter(slug=slug).count():
                raise IntegrityError("code already exists")

        while 1:
            eventLink = EventLink()
            eventLink.save()
            try:
                with transaction.atomic():
                    eventLink.event = self
                    if slug:
                        eventLink.slug = slug
                    else:
                        eventLink.slug = EventLink.encode_hash(eventLink.pk)
                    eventLink.save()
            except (IntegrityError) as e:
                if slug:
                    raise e
            else:
                return eventLink

    def links(self):
        return EventLink.objects.filter(event=self)

    def create_eventinvites(self, items, default_country):
        invites = []
        errs = []
        if not items:
            return None, True, "No items given"
        for item in items:
            phone_number = item[1]
            try:
                phone_number = phonenumbers.parse(phone_number, default_country)
                if not phonenumbers.is_possible_number(phone_number):
                    raise NumberParseException(None, None)
            except NumberParseException:
                errs.append(item[1])
            else:
                invite = EventInvite(
                    nickname=item[0],
                    phone_number=phonenumbers.format_number(
                        phone_number,
                        phonenumbers.PhoneNumberFormat.E164,
                    ),
                )
                invites.append(invite)
        if errs:
            return errs, True, "Unable to parse the following:"

        added = []
        for invite in invites:
            with transaction.atomic():
                try:
                    self.eventinvite_set.add(invite)
                except IntegrityError as e:
                    pass
                else:
                    added.append(invite)
        if added:
            return added, False, None
        else:
            return None, True, "All duplicates"

    def send_invites(self, eventinvites):
        sms_template = string.Template(self.sms_message)

        now = timezone.now()

        for eventinvite in eventinvites:
            memberidentifier = eventinvite.to_memberidentifier()

            def sms_formatter(link_code_object):
                return sms_template.safe_substitute(
                    name=eventinvite.nickname,
                )

            sms_analytics_event_name = 'Event SMS Invite Sent'
            sms_analytics_event_properties = { 'event': str(self.id) }
            self.album.add_members(self.created_by, [memberidentifier], now, sms_formatter, sms_analytics_event_name, sms_analytics_event_properties)

    def eventinvites(self):
        return self.eventinvite_set.all()

    def __unicode__(self):
        return u"{0}: {1}".format(self.organization.code, self.name)


class EventInvite(models.Model):
    event = models.ForeignKey(Event)
    nickname = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=32)

    class Meta:
        unique_together = ('event', 'phone_number')

    def get_phone_number(self):
        return PhoneNumber.objects.filter(phone_number=self.phone_number).first()

    def get_phone_number_link_code(self):
        return PhoneNumberLinkCode.objects.filter(phone_number__phone_number=self.phone_number).first()

    def is_added_to_event(self):
        phone_number = self.get_phone_number()
        if phone_number:
            return self.event.album.is_user_member(phone_number.user.id)
        else:
            return False

    def is_registered_user(self):
        phone_number = self.get_phone_number()
        if phone_number:
            return phone_number.verified
        else:
            return False

    def to_memberidentifier(self):
        from photos_api.serializers import MemberIdentifier
        return MemberIdentifier(
            phone_number=self.phone_number,
            contact_nickname=self.nickname,
        )

    @staticmethod
    def import_data(data):
        lines = data.splitlines()
        ret = []
        matcher = re.compile(r'^(.*)(\s+)((\+)?[0-9\- ]+)$')
        for line in lines:
            matches = matcher.match(line.strip())
            if matches:
                ret.append((matches.group(1), matches.group(3)))
        return ret

    def __unicode__(self):
        return u"{0} - {1}".format(self.nickname, self.phone_number)


VALID_LINK_CHARS = tuple(string.ascii_letters + string.digits)


class EventLink(models.Model):
    slug = models.CharField(max_length=255, unique=True, null=True, blank=True)
    event = models.ForeignKey(Event, null=True)
    time_sent = models.DateTimeField(null=True, blank=True)
    visited_count = models.IntegerField(default=0)
    downloaded_count = models.IntegerField(default=0)

    def incr_visited(self):
        self.visited_count = models.F('visited_count') + 1
        self.save()

    def incr_downloaded(self):
        self.downloaded_count = models.F('downloaded_count') + 1
        self.save()

    def get_absolute_url(self):
        return reverse('affiliates.views.event_link', args=[self.slug])

    def __unicode__(self):
        return self.get_absolute_url()

    @staticmethod
    def encode_hash(i):
        if i == 0:
            return VALID_LINK_CHARS[0]
        s = []
        base = len(VALID_LINK_CHARS)
        while i > 0:
            s.append(VALID_LINK_CHARS[i % base])
            i = i / base
        return "".join(reversed(s))

    @staticmethod
    def decode_hash(h):
        i = 0
        base = len(VALID_LINK_CHARS)
        try:
            for c in h:
                i = i * base + VALID_LINK_CHARS.index(c)
        except ValueError:
            return None
        return i
