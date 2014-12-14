from django.contrib import auth
from django.contrib.auth import get_user_model
import os
import random
import datetime

from django.conf import settings
from django.db import models
from django.utils import timezone

import phonenumbers

from phone_auth.models import PhoneNumber, PhoneNumberLinkCode
from photos import image_uploads
from photos_api.signals import members_added_to_album, album_created
from photos_api import device_push


class AlbumManager(models.Manager):
    def create_album(self, creator, name, date_created=None):

        # Date added is current datetime by default
        if date_created is None:
            date_created = timezone.now()

        album = self.create(
                date_created = date_created,
                name = name,
                creator = creator,
                last_updated = date_created,
                revision_number = 0
                )

        AlbumMember.objects.create(
            user = creator,
            album = album,
            datetime_added = date_created,
            added_by_user = creator
        )
        album_created.send(sender=self, album=album)

        return album

    def get_user_albums(self, user_id):
        return Album.objects.filter(memberships__user__id=user_id)


class Album(models.Model):
    date_created = models.DateTimeField()
    name = models.CharField(max_length=255)
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='+')
    last_updated = models.DateTimeField()
    revision_number = models.IntegerField()

    objects = AlbumManager()

    def save_revision(self, revision_date):
        self.last_updated = revision_date
        Album.objects.filter(pk=self.id).update(revision_number=models.F('revision_number')+1)
        self.save(update_fields=['last_updated'])

    @staticmethod
    def default_sms_message_formatter(link_code):
        return link_code.inviting_user.nickname + ' has shared photos with you!'

    class ModificationContext(object):
        """
        All modifications of an album must go through this. Makes sure that an
        album revision is saved at the end of all modifications

        Example usage:

            album = Album.objects.get(pk=42)
            with album.modify(timezone.now()) as m:
                m.add_user_id(801)
                m.add_user_id(802)

        """
        def __init__(self, album, current_date):
            self.album = album
            self.current_date = current_date

        def __enter__(self):
            return self

        def __exit__(self, type, value, traceback):
            self.album.save_revision(self.current_date)

        def add_user_id(self, inviter, user_id):
            """
            Returns True is user_id succesfully added, or False if no such user_id exists
            """
            try:
                added_user = get_user_model().objects.get(pk=user_id)
            except get_user_model().DoesNotExist:
                return False

            _, created = AlbumMember.objects.get_or_create(user=added_user, album=self.album, defaults={
                'added_by_user': inviter,
                'datetime_added': self.current_date
                })

            if created:
                members_added_to_album.send(sender=None, member_users=[added_user], by_user=inviter, to_album=self.album)

            return True

        def add_phone_number(self, inviter, parsed_phone_number, contact_nickname, send_invite_callable):
            """
            inviter: The user who added the friend

            parsed_phone_number: A result of the phonenumbers.parse() function

            contact_nickname: A string that will be the username of the new friend

            send_invite_callable: A callable that accepts 3 parameters:
            inviter, phone_number, current_time

            Returns the PhoneNumber object belonging to the user who was added
            """
            if not isinstance(parsed_phone_number, phonenumbers.phonenumber.PhoneNumber):
                raise ValueError('phone must be a PhoneNumber object')

            phone_number_str = phonenumbers.format_number(parsed_phone_number, phonenumbers.PhoneNumberFormat.E164)

            phone_number, _ = PhoneNumber.objects.get_or_create_phone_number(phone_number_str, contact_nickname, self.current_date)

            _, member_created = AlbumMember.objects.get_or_create(user=phone_number.user, album=self.album, defaults={
                'added_by_user': inviter,
                'datetime_added': self.current_date
                })

            if phone_number.verified:
                if member_created:
                    members_added_to_album.send(sender=None, member_users=[phone_number.user], by_user=inviter, to_album=self.album)
            else:
                if send_invite_callable:
                    send_invite_callable(inviter, phone_number, self.current_date)

            return phone_number

        def comment_on_photo(self, photo, commenter, client_msg_id, comment_text):
            if photo.album != self.album:
                raise ValueError('photo is not part of this album')

            # TODO Detect duplicate client_msg_id and ignore

            PhotoComment.objects.create(
                    photo = photo,
                    date_created = self.current_date,
                    author = commenter,
                    client_msg_id = client_msg_id,
                    comment_text = comment_text
                    )

            comment_thread_author_ids = set()
            for comment in PhotoComment.objects.filter(photo=photo).exclude(author=commenter).only('author'):
                comment_thread_author_ids.add(comment.author.id)

            device_push.broadcast_photo_comment(comment_thread_author_ids, commenter.nickname, photo.album.id, photo.photo_id, photo.album.name)

        def glance_photo(self, photo, glancer, emoticon_name):
            if photo.album != self.album:
                raise ValueError('photo is not part of this album')

            photo_glance, created = PhotoGlance.objects.get_or_create(
                    photo = photo,
                    author = glancer,
                    defaults = {
                        'date_created': self.current_date,
                        'emoticon_name': emoticon_name
                        })
            if not created:
                photo_glance.date_created = self.current_date
                photo_glance.emoticon_name = emoticon_name
                photo_glance.save(update_fields=['date_created', 'emoticon_name'])

            device_push.broadcast_photo_glance(photo.author.id, glancer.nickname, photo.album.id, photo.album.name)


    def modify(self, current_date):
        return Album.ModificationContext(self, current_date)

    def add_members(self, inviter, member_identifiers, date_added, sms_message_formatter, sms_analytics_event_name='New User SMS Invite Sent', sms_analytics_event_properties={}):
        """
        This method is deprecated and will eventually be removed
        """
        result = []

        new_users = []

        for member_identifier in member_identifiers:
            if member_identifier.user_id is None:

                try:
                    number = phonenumbers.parse(member_identifier.phone_number,
                                                member_identifier.default_country)
                except phonenumbers.phonenumberutil.NumberParseException:
                    result.append({"success": False, "error": "invalid_phone_number"})
                    continue

                if not phonenumbers.is_possible_number(number):
                    result.append({"success": False, "error": "not_possible_phone_number"})
                    continue

                # Format final number.
                formatted_number = phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.E164)

                user = PhoneNumberLinkCode.objects.invite_phone_number(
                        inviter,
                        formatted_number,
                        member_identifier.contact_nickname,
                        date_added,
                        sms_message_formatter,
                        sms_analytics_event_name,
                        sms_analytics_event_properties)
                new_users.append(user)

                # Later check for the result of the Twilio SMS send, which
                # will tell us if sending the SMS failed due to being an invalid
                # number. In this save success=False, error=invalid_phone_number
                result.append({"success": True})

            else:
                try:
                    new_users.append(get_user_model().objects.get(
                        pk=member_identifier.user_id))
                    result.append({"success": True})
                except get_user_model().DoesNotExist, err:
                    result.append({"success": False, "error": "invalid_user_id"})

        # Create memberships
        for new_user in new_users:
            defaults = {
                'added_by_user': inviter,
                'datetime_added': date_added
            }
            AlbumMember.objects.get_or_create(user=new_user, album=self, defaults=defaults)

        # TODO Modify this to allow a custom push notification
        members_added_to_album.send(sender=self, member_users=new_users,
                                    by_user=inviter, to_album=self)

        self.save_revision(date_added)

        return result

    def __unicode__(self):
        return self.name

    def get_photos(self):
        return self.photo_set.order_by('album_index')

    def get_latest_photos(self):
        return self.photo_set.order_by('-album_index')[:2]

    def get_invite_page_photos(self):
        return self.photo_set.order_by('-album_index')[:4]

    def is_user_member(self, user_id):
        return AlbumMember.objects.filter(album=self, user__pk=user_id).exists()

    def get_etag(self):
        return u'{0}'.format(self.revision_number)

    def get_member_users(self):
        return [membership.user for membership in AlbumMember.objects.filter(album=self).only('user')]

    def get_num_new_photos(self, since_date, user_id):
        queryset = self.photo_set.exclude(author__id=user_id)

        if since_date:
            # due to serializer issues, since_date is accurate only up to a millisecond
            # while the database is accurate up to a microsecond
            since_date = since_date + datetime.timedelta(milliseconds=1)
            return queryset.filter(date_created__gt=since_date).count()
        else:
            return queryset.count()


class AlbumMemberManager(models.Manager):
    def get_user_memberships(self, user_id):
        return AlbumMember.objects.filter(user__id=user_id).select_related('album')


class AlbumMember(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="album_membership")
    album = models.ForeignKey(Album, related_name="memberships")

    added_by_user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="created_album_memberships")
    datetime_added = models.DateTimeField()

    last_access = models.DateTimeField(null=True, blank=True)

    objects = AlbumMemberManager()

    class Meta:
        db_table = "photos_album_members"
        unique_together = ('user', 'album')

    def __unicode__(self):
        return u"Member {0} of album {1} (Membership #{2})".format(self.user, self.album, self.pk)

    def get_num_new_photos(self):
        return self.album.get_num_new_photos(self.last_access, self.user.id)

    def update_last_access(self, timestamp):
        if self.last_access is None or self.last_access < timestamp:
            self.last_access = timestamp
            self.save(update_fields=['last_access'])


class PhotoManager(models.Manager):
    def upload_request(self, author):
        success = False
        while not success:
            new_photo_id = Photo.generate_photo_id()
            new_storage_id = Photo.generate_photo_id()

            new_pending_photo = PendingPhoto.objects.create(
                    photo_id = new_photo_id,
                    storage_id = new_storage_id,
                    file_uploaded_time = None,
                    processing_done_time = None,
                    start_time = timezone.now(),
                    author = author
                    )

            # Make sure that there is no existing Photo with the same id

            if (not Photo.objects.filter(photo_id=new_photo_id).exists() and
                   not Photo.objects.filter(storage_id=new_storage_id).exists()):
                success = True
            else:
                new_pending_photo.delete()

        return new_pending_photo


class Photo(models.Model):
    photo_id = models.CharField(primary_key=True, max_length=128)
    storage_id = models.CharField(max_length=128, db_index=True)
    subdomain = models.CharField(max_length=64)
    date_created = models.DateTimeField(db_index=True)
    author = models.ForeignKey(settings.AUTH_USER_MODEL)
    album = models.ForeignKey(Album)
    album_index = models.PositiveIntegerField(db_index=True)

    objects = PhotoManager()

    class Meta:
        unique_together = (('album', 'album_index'),)
        get_latest_by = 'album_index'
        ordering = ['album_index']

    def __unicode__(self):
        return self.photo_id

    @staticmethod
    def generate_photo_id():
        key_bitsize = 256
        return ''.join(["{0:02x}".format(ord(c)) for c in os.urandom(key_bitsize / 8)])

    def get_photo_url(self):
        if settings.USING_LOCAL_PHOTOS:
            return '/photos/' + self.subdomain + '/' + self.photo_id + '.jpg'
        else:
            return settings.PHOTO_SERVER_URL_FORMAT_STR.format(self.subdomain, self.photo_id + '.jpg')

    def get_photo_url_no_ext(self):
        """
        Returns the url without the ".jpg" suffix
        """
        return self.get_photo_url()[:-4]

    def get_image_dimensions(self, image_size_str=None):
        if not image_size_str:
            # Original Image dimensions
            return (self.width, self.height)

        image_dimensions_calculator = image_uploads.image_sizes[image_size_str]
        return image_dimensions_calculator.get_image_dimensions(self.width, self.height)

    def get_comments(self):
        return self.photocomment_set.order_by('date_created')

    def get_glances(self):
        return self.photoglance_set.order_by('date_created')


def get_pending_photo_default_photo_id():
    photo_id_generated = False
    photo_id = None
    while not photo_id_generated:
        photo_id = Photo.generate_photo_id()
        # Make sure that there is no existing Photo with the same id
        if Photo.objects.filter(pk=photo_id).exists():
            continue
        photo_id_generated = True
    return photo_id

class PendingPhoto(models.Model):
    photo_id = models.CharField(primary_key=True, max_length=128)
    storage_id = models.CharField(unique=True, max_length=128)
    file_uploaded_time = models.DateTimeField(null=True)
    processing_done_time = models.DateTimeField(null=True)
    start_time = models.DateTimeField(default=timezone.now)
    author = models.ForeignKey(settings.AUTH_USER_MODEL)

    def set_uploaded(self, upload_time):
        if upload_time is None:
            raise TypeError('upload_time must not be None')

        self.file_uploaded_time = upload_time
        self.save(update_fields=['file_uploaded_time'])

    def is_file_uploaded(self):
        return not (self.file_uploaded_time is None)

    def set_processing_done(self, done_time):
        if done_time is None:
            raise TypeError('upload_time must not be None')

        if not self.is_file_uploaded():
            raise ValueError("can't set_processing_done when not yet is_file_uploaded")

        self.processing_done_time = done_time
        self.save(update_fields=['processing_done_time'])

    def is_processing_done(self):
        return not (self.processing_done_time is None)


class PhotoComment(models.Model):
    photo = models.ForeignKey(Photo)
    date_created = models.DateTimeField(db_index=True)
    author = models.ForeignKey(settings.AUTH_USER_MODEL)
    client_msg_id = models.BigIntegerField(db_index=True)
    comment_text = models.TextField()

    class Meta:
        unique_together = ('photo', 'author', 'client_msg_id')

    # TODO ...


class PhotoGlance(models.Model):
    photo = models.ForeignKey(Photo)
    emoticon_name = models.CharField(max_length=255)
    date_created = models.DateTimeField(db_index=True)
    author = models.ForeignKey(settings.AUTH_USER_MODEL)

    GLANCE_EMOTICONS_BASE_URL = 'https://glance-emoticons.s3.amazonaws.com/'

    class Meta:
        unique_together = ('photo', 'author')

    def __unicode__(self):
        return unicode(self.photo) + ' ' + unicode(self.author) + ': ' + self.emoticon_name


# This is a temporary solution until a more robust coordinator is implemented
class PhotoServer(models.Model):
    photos_update_url = models.CharField(max_length=255, unique=True)
    subdomain = models.CharField(max_length=64, db_index=True)
    auth_key = models.CharField(max_length=128)
    date_registered = models.DateTimeField()
    unreachable = models.BooleanField()

    def __unicode__(self):
        result = ''
        if self.unreachable:
            result += '[UNREACHABLE] '
        result += self.subdomain + ': ' + self.photos_update_url
        return result

    def set_unreachable(self):
        self.unreachable = True
        self.save(update_fields=['unreachable'])
