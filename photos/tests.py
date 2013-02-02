import datetime

from django.contrib import auth
from django.test import TestCase
from django.utils.timezone import utc

from photos.models import Album, Photo, PendingPhoto

class ModelTest(TestCase):
    fixtures = ['tests/test_users']

    def setUp(self):
        self.amanda = auth.get_user_model().objects.get(username='amanda')
        self.barney = auth.get_user_model().objects.get(username='barney')

    def test_create_new_album(self):
        the_date = datetime.datetime(2010, 1, 1, tzinfo=utc)
        album = Album.objects.create_album(self.amanda, 'Ski Trip', the_date)

        self.assertTrue(album.is_user_member(self.amanda.id))
        self.assertFalse(album.is_user_member(self.barney.id))

        self.assertEqual(list(Album.objects.get_user_albums(self.amanda.id)), [album])
        self.assertEqual(list(Album.objects.get_user_albums(self.barney.id)), [])

        photo_id = Photo.objects.upload_request(self.amanda)
        self.assertTrue(PendingPhoto.objects.filter(photo_id=photo_id).exists())

        # Pretend that the photo was uploaded
        new_photo = Photo.objects.upload_to_album(photo_id, album, the_date)

        self.assertFalse(PendingPhoto.objects.filter(photo_id=photo_id).exists())

        # These are the dummy values that are currently hardcoded:
        self.assertEqual(new_photo.width, 640)
        self.assertEqual(new_photo.height, 480)

        self.assertEqual(list(album.get_photos()), [new_photo])

    def test_album_last_updated_photo_upload(self):
        create_date = datetime.datetime(2010, 1, 1, tzinfo=utc)

        the_album = Album.objects.create_album(self.amanda, 'Ski Trip', create_date)
        self.assertEqual(the_album.last_updated, create_date)

        update_date = datetime.datetime(2010, 1, 2, tzinfo=utc)

        photo_id = Photo.objects.upload_request(self.amanda)
        # Pretend that the photo was uploaded
        Photo.objects.upload_to_album(photo_id, the_album, update_date)

        self.assertEqual(the_album.last_updated, update_date)
