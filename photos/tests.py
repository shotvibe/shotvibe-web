import datetime

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils.timezone import utc

from photos.models import Album, Photo, PendingPhoto

class ModelTest(TestCase):
    fixtures = ['tests/test_users']

    def setUp(self):
        self.amanda = User.objects.get(username='amanda')
        self.barney = User.objects.get(username='barney')

    def test_create_new_album(self):
        the_date = datetime.datetime(2010, 1, 1, tzinfo=utc)
        album = Album.objects.create_album(self.amanda, 'Ski Trip', the_date)

        self.assertTrue(album.is_user_member(self.amanda.id))
        self.assertFalse(album.is_user_member(self.barney.id))

        self.assertEqual(Album.objects.get_user_albums(self.amanda.id)[0], album)
        self.assertFalse(Album.objects.get_user_albums(self.barney.id))

        photo_id = Photo.objects.upload_request(self.amanda)
        self.assertTrue(PendingPhoto.objects.filter(photo_id=photo_id).exists())

        # Pretend that the photo was uploaded
        new_photo = Photo.objects.upload_to_album(photo_id, album, the_date)

        self.assertFalse(PendingPhoto.objects.filter(photo_id=photo_id).exists())

        # These are the dummy values that are currently hardcoded:
        self.assertEqual(new_photo.width, 640)
        self.assertEqual(new_photo.height, 480)
