import uuid
import random

from django.conf import settings
from django.db import models
from django.utils import timezone

from photos.image_processing import process_uploaded_image

class AlbumManager(models.Manager):
    def create_album(self, creator, name, date_created):
        album = self.create(
                date_created = date_created,
                name = name,
                creator = creator,
                last_updated = date_created
                )
        album.members.add(creator.id)
        return album

    def get_user_albums(self, user_id):
        return self.filter(members__id=user_id)

class Album(models.Model):
    date_created = models.DateTimeField()
    name = models.CharField(max_length=255)
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='+')
    members = models.ManyToManyField(settings.AUTH_USER_MODEL)
    last_updated = models.DateTimeField()

    objects = AlbumManager()

    def __unicode__(self):
        return u'{0} {1}'.format(self.id, self.name)

    def get_photos(self):
        return self.photo_set.all()

    def is_user_member(self, user_id):
        return self.members.filter(id=user_id).exists()

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
            new_id = unicode(uuid.uuid4())

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
        pending_photo = PendingPhoto.objects.get(photo_id=photo_id)

        # TODO catch exception:
        width, height = process_uploaded_image(pending_photo.bucket, photo_id)

        new_photo = Photo.objects.create(
                photo_id=photo_id,
                bucket=pending_photo.bucket,
                date_created=date_created,
                author=pending_photo.author,
                album=album,
                width=width,
                height=height)

        pending_photo.delete()

        album.last_updated = date_created
        album.save(update_fields=['last_updated'])

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

    def get_photo_url(self):
        location, directory = self.bucket.split(':')
        if location == 'local':
            return settings.LOCAL_PHOTO_BUCKET_URL_FORMAT_STR.format(directory, self.photo_id)
        else:
            raise ValueError('Unknown photo bucket location: ' + location)

class PendingPhoto(models.Model):
    photo_id = models.CharField(primary_key=True, max_length=128)
    bucket = models.CharField(max_length=64)
    start_time = models.DateTimeField()
    author = models.ForeignKey(settings.AUTH_USER_MODEL)
