import re
import string
import phonenumbers

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
    html_content = models.CharField(max_length=255)

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
                    eventLink.slug = slug if slug else EventLink.encode_hash(eventLink.pk)
                    eventLink.save()
            except (IntegrityError) as e:
                if slug:
                    raise e 
            else:
                return eventLink

    def links(self):
        return EventLink.objects.filter(event=self)

    def create_eventinvitequeue(self, items):
        eiqs = []
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
                    raise phonenumbers.phonenumberutil.NumberParseException(None, None)
            except phonenumbers.phonenumberutil.NumberParseException:
                errs.append(item[1])
            else:
                eiq = EventInviteQueue(
                    nickname=item[0],
                    phone_number=item[1],
                )
                eiqs.append(eiq)
        if errs:
            return errs, True, "Unable to parse the following:"

        added = []
        for eiq in eiqs:
            with transaction.atomic():
                try:
                    self.eventinvitequeue_set.add(eiq)
                except IntegrityError:
                    pass
                else:
                    added.append(eiq)
        if added:
            return added, False, None
        else:
            return None, True, "All duplicates"

    def eventinvitequeue(self):
        return self.eventinvitequeue_set.all()

    def __unicode__(self):
        return u"{0}: {1}".format(self.organization.name, self.name)


class EventInviteQueue(models.Model):
    event = models.ForeignKey(Event)
    nickname = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=32, unique=True)

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
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True)
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
        return self.user is not None

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
