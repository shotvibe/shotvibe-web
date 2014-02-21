import re
import string
import phonenumbers
from operator import methodcaller
from phonenumbers.phonenumberutil import NumberParseException

from django.db import models, transaction, IntegrityError
from django.conf import settings
from django.core.urlresolvers import reverse

from photos.models import Album
from photos_api.serializers import MemberIdentifier


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


class Event(models.Model):
    organization = models.ForeignKey(Organization)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL)
    album = models.ForeignKey(Album)
    name = models.CharField(max_length=255)
    time = models.DateTimeField()
    sms_message = models.CharField(max_length=255)
    push_notification = models.CharField(max_length=255)
    location = models.CharField(max_length=255)
    #logo =
    #banner
    html_content = models.TextField()

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

    def public_links(self):
        return EventLink.objects.filter(event=self, invite__isnull=True)

    def create_eventinvites(self, items):
        invites = []
        errs = []
        if not items:
            return None, True, "No items given"
        for item in items:
            if not item[1].startswith('+'):
                phone_number = '+' + item[1]
            else:
                phone_number = item[1]
            try:
                phone_number = phonenumbers.parse(phone_number, None)
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
        for eventinvite in eventinvites:
            invitelink = eventinvite.create_invitelink()
            memberidentifier = eventinvite.to_memberidentifier()
            def sms_formatter(link_code_object):
                formatted_sms = sms_template.safe_substitute(
                    name=eventinvite.nickname,
                )
                return u"{0} https://www.shotvibe.com{1}".format(
                    formatted_sms,
                    invitelink.get_absolute_url(),
                )
            self.album.add_members(self.created_by, [memberidentifier], message_formatter=sms_formatter)

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

    def to_memberidentifier(self):
        return MemberIdentifier(
            phone_number=self.phone_number,
            contact_nickname=self.nickname,
        )

    def create_invitelink(self):
        try:
            return self.eventlink
        except EventLink.DoesNotExist:
            pass
        eventlink = self.event.create_link()
        eventlink.invite = self
        eventlink.save()
        return eventlink

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
        return "{0} - {1}".format(self.nickname, self.phone_number)


VALID_LINK_CHARS = tuple(string.ascii_letters + string.digits)


class EventLink(models.Model):
    slug = models.CharField(max_length=255, unique=True, null=True, blank=True)
    event = models.ForeignKey(Event, null=True)
    invite = models.OneToOneField(EventInvite, null=True)
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

    @property
    def is_personal(self):
        return self.invite is not None

    @property
    def is_public(self):
        return not self.is_personal

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
