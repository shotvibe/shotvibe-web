from django.contrib import auth
import os
import random

from django.conf import settings
from django.db import models
from django.utils import timezone

from phone_auth.models import PhoneNumber, PhoneNumberLinkCode
from photos import image_uploads
from photos_api import device_push

class AlbumManager(models.Manager):
    def create_album(self, creator, name, date_created):
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

        return album

    def get_user_albums(self, user_id):
        album_memberships = AlbumMember.objects.filter(user__pk=user_id).select_related("album").only("album__id")
        album_ids = [am.album.pk for am in album_memberships]
        return Album.objects.filter(pk__in=album_ids)

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

    def add_members(self, inviter, user_ids, phone_number_strs=None, date_added=None):

        if not phone_number_strs:
            phone_number_strs = []

        # Date added is current datetime by default
        if not date_added:
            date_added = timezone.now()

        # List of users to add. Start with users from user_ids.
        new_users = [auth.get_user_model().objects.get(pk=user_id) for user_id in user_ids]

        # Add users that was requested by phone number
        for phone_number_str in phone_number_strs:
            try:
                phone_number = PhoneNumber.objects.get(phone_number=phone_number_str)
                if phone_number.should_send_invite():
                    PhoneNumberLinkCode.objects.invite_existing_phone_number(phone_number, inviter, date_added)
                new_users.append(phone_number.user)
            except PhoneNumber.DoesNotExist:
                link_code_object = PhoneNumberLinkCode.objects.invite_new_phone_number(phone_number_str, inviter, date_added)
                new_users.append(link_code_object.phone_number.user)

        # Create memberships
        for new_user in new_users:
            AlbumMember.objects.create(
                user = new_user,
                album = self,
                added_by_user = inviter,
                datetime_added = date_added
            )


        self.save_revision(date_added)

    def __unicode__(self):
        return self.name

    def get_photos(self):
        return self.photo_set.order_by('date_created', 'photo_id')

    def get_latest_photos(self):
        return self.photo_set.order_by('-date_created', '-photo_id')[:2]

    def is_user_member(self, user_id):
        return AlbumMember.objects.filter(album=self, user__pk=user_id).exists()

    def get_etag(self):
        return u'{0}'.format(self.revision_number)

    def add_photos(self, author, photo_ids):
        now = timezone.now()
        for photo_id in photo_ids:
            # TODO Catch exception
            Photo.objects.upload_to_album(photo_id, self, now)

        device_push.broadcast_photos_added(
                album_id = self.id,
                author_id = author.id,
                album_name = self.name,
                author_name = author.nickname,
                num_photos = len(photo_ids),
                user_ids = [membership.user.id for membership in AlbumMember.objects.filter(album=self).only('user__id')])

    def get_member_users(self):
        return [membership.user for membership in AlbumMember.objects.filter(album=self).only('user')]


class AlbumMember(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="album_membership")
    album = models.ForeignKey(Album, related_name="memberships")

    added_by_user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="created_album_memberships")
    datetime_added = models.DateTimeField()

    class Meta:
        db_table = "photos_album_members"
        unique_together = ('user', 'album')

    def __unicode__(self):
        return "Member {0} of album {1} (Membership #{2})".format(self.user, self.album, self.pk)


all_photo_buckets = (
        'local:photos01',
        'local:photos02',
        'local:photos03',
        'local:photos04',
        )

class PhotoManager(models.Manager):
    def upload_request(self, author):
        success = False
        while not success:
            new_id = Photo.generate_photo_id()

            new_pending_photo = PendingPhoto.objects.create(
                    photo_id = new_id,
                    bucket = random.choice(all_photo_buckets),
                    start_time = timezone.now(),
                    author = author
                    )

            # Make sure that there is no existing Photo with the same id

            if not Photo.objects.filter(photo_id=new_id).exists():
                success = True
            else:
                new_pending_photo.delete()

        return new_id

    def upload_to_album(self, photo_id, album, date_created):
        try:
            return Photo.objects.get(photo_id=photo_id)
        except Photo.DoesNotExist:
            pass

        try:
            pending_photo = PendingPhoto.objects.get(photo_id=photo_id)
        except PendingPhoto.DoesNotExist:
            # TODO Better exception
            raise

        # TODO catch exception:
        width, height = image_uploads.process_uploaded_image(pending_photo.bucket, photo_id)

        new_photo = Photo.objects.create(
                photo_id=photo_id,
                bucket=pending_photo.bucket,
                date_created=date_created,
                author=pending_photo.author,
                album=album,
                width=width,
                height=height)

        pending_photo.delete()

        album.save_revision(date_created)

        return new_photo

class Photo(models.Model):
    photo_id = models.CharField(primary_key=True, max_length=128)
    bucket = models.CharField(max_length=64)
    date_created = models.DateTimeField(db_index=True)
    author = models.ForeignKey(settings.AUTH_USER_MODEL)
    album = models.ForeignKey(Album)
    width = models.IntegerField()
    height = models.IntegerField()

    objects = PhotoManager()

    class Meta:
        get_latest_by = 'date_created'

    def __unicode__(self):
        return self.photo_id

    @staticmethod
    def generate_photo_id():
        key_bitsize = 256
        return ''.join(["{0:02x}".format(ord(c)) for c in os.urandom(key_bitsize / 8)])

    def get_photo_url(self):
        location, directory = self.bucket.split(':')
        if location == 'local':
            return settings.LOCAL_PHOTO_BUCKET_URL_FORMAT_STR.format(directory, self.photo_id)
        else:
            raise ValueError('Unknown photo bucket location: ' + location)

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

class PendingPhoto(models.Model):
    photo_id = models.CharField(primary_key=True, max_length=128)
    bucket = models.CharField(max_length=64)
    start_time = models.DateTimeField()
    author = models.ForeignKey(settings.AUTH_USER_MODEL)
