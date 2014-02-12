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

    def add_members(self, inviter, member_identifiers, date_added=None):

        result = []

        # Date added is current datetime by default
        if not date_added:
            date_added = timezone.now()

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

                try:
                    phone_number = PhoneNumber.objects.get(
                        phone_number=formatted_number)
                    if phone_number.should_send_invite():
                        PhoneNumberLinkCode.objects.\
                            invite_existing_phone_number(inviter, phone_number,
                                                         date_added)
                    new_users.append(phone_number.user)
                except PhoneNumber.DoesNotExist:
                    link_code_object = PhoneNumberLinkCode.objects.\
                        invite_new_phone_number(inviter,
                                                formatted_number,
                                                member_identifier.contact_nickname,
                                                date_added)
                    new_users.append(link_code_object.phone_number.user)

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
