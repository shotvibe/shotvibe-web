from django.contrib import auth
from django.db.models import Max
import os
import random

from django.conf import settings
from django.db import models
from django.utils import timezone

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

        # Date added is current datetime by default
        if not date_added:
            date_added = timezone.now()

        new_users = []

        # New users by user_id
        member_ids = [mi.user_id for mi in member_identifiers if mi.user_id is not None]
        new_users = new_users + list(auth.get_user_model().objects.filter(pk__in=member_ids))

        # New users by phone_number
        member_identifiers_with_phones = [mi for mi in member_identifiers if mi.user_id is None]
        for member_identifier in member_identifiers_with_phones:
            try:
                phone_number = PhoneNumber.objects.get(phone_number=member_identifier.phone_number)
                if phone_number.should_send_invite():
                    PhoneNumberLinkCode.objects.invite_existing_phone_number(inviter, phone_number, date_added)
                new_users.append(phone_number.user)
            except PhoneNumber.DoesNotExist:
                link_code_object = PhoneNumberLinkCode.objects.invite_new_phone_number(inviter,
                                                                                       member_identifier.phone_number,
                                                                                       member_identifier.contact_nickname,
                                                                                       date_added)
                new_users.append(link_code_object.phone_number.user)

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

    def __unicode__(self):
        return self.name

    def get_photos(self):
        return self.photo_set.order_by('date_created', 'photo_id')

    def get_latest_photos(self):
        return self.photo_set.order_by('-date_created', '-photo_id')[:2]

    def get_invite_page_photos(self):
        return self.photo_set.order_by('-date_created', '-photo_id')[:4]

    def is_user_member(self, user_id):
        return AlbumMember.objects.filter(album=self, user__pk=user_id).exists()

    def get_etag(self):
        return u'{0}'.format(self.revision_number)

    def get_member_users(self):
        return [membership.user for membership in AlbumMember.objects.filter(album=self).only('user')]

    def get_num_new_photos(self, since_date):
        if since_date:
            return self.photo_set.filter(date_created__gt=since_date).count()
        else:
            return self.photo_set.count()


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
        return self.album.get_num_new_photos(self.last_access)

    def update_last_access(self, timestamp):
        if self.last_access is None or self.last_access < timestamp:
            self.last_access = timestamp
            self.save(update_fields=['last_access'])


all_photo_buckets = (
        'local:photos01',
        'local:photos02',
        'local:photos03',
        'local:photos04',
        )


class PhotoManager(models.Manager):
    pass


class Photo(models.Model):
    photo_id = models.CharField(primary_key=True, max_length=128)
    bucket = models.CharField(max_length=64)
    date_created = models.DateTimeField(db_index=True)
    author = models.ForeignKey(settings.AUTH_USER_MODEL)
    album = models.ForeignKey(Album)
    album_index = models.PositiveIntegerField(db_index=True)
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

def get_pending_photo_default_bucket():
    return random.choice(all_photo_buckets)

class PendingPhoto(models.Model):
    photo_id = models.CharField(primary_key=True, max_length=128, default=get_pending_photo_default_photo_id)
    bucket = models.CharField(max_length=64, choices=zip(all_photo_buckets, all_photo_buckets),
                              default=get_pending_photo_default_bucket)
    start_time = models.DateTimeField(default=timezone.now)
    author = models.ForeignKey(settings.AUTH_USER_MODEL)

    def get_or_process_uploaded_image_and_create_photo(self, album, date_created):
        """
        For already uploaded photos it will simply return photo.
        For pending photo it will process uploaded image, create Photo object and return it.
        """
        try:
            photo = Photo.objects.get(photo_id=self.photo_id)
        except Photo.DoesNotExist:
            pass
        else:
            return photo

        # TODO catch exception:
        width, height = image_uploads.process_uploaded_image(self.bucket, self.photo_id)

        album_index_q = Photo.objects.filter(album=album)\
            .aggregate(Max('album_index'))
        album_index = album_index_q['album_index__max']
        if album_index is None:
            album_index = 0
        else:
            album_index += 1

        new_photo = Photo.objects.create(
            photo_id=self.photo_id,
            bucket=self.bucket,
            date_created=date_created,
            author=self.author,
            album=album,
            album_index=album_index,
            width=width,
            height=height
        )

        self.delete()

        album.save_revision(date_created)

        return new_photo
