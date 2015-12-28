import datetime

from django.test import TestCase
from django.test.utils import override_settings
from django.utils.timezone import utc

from phone_auth.models import User
from photos.models import Album
from welcome_album.models import WELCOME_ALBUM_DELAY, ScheduledWelcomeAlbumJob

import welcome_album


class WelcomeAlbumTest(TestCase):
    def setUp(self):
        self.amanda = User.objects.create_user('amanda')
        self.bob = User.objects.create_user('bob')

        self.welcome_album = Album.objects.create_album(self.amanda, 'Welcome', datetime.datetime(2000, 01, 01, tzinfo=utc))

    def test_create_welcome_album(self):
        with override_settings(WELCOME_ALBUM_ID=self.welcome_album.id):
            welcome_album.create_welcome_album(self.bob, datetime.datetime(2000, 01, 02, 0, 0, 0, tzinfo=utc))

    def test_scheduled_jobs(self):
        with override_settings(WELCOME_ALBUM_ID=self.welcome_album.id):
            ScheduledWelcomeAlbumJob.objects.schedule_job(self.bob, datetime.datetime(2000, 01, 02, 0, 0, 0, tzinfo=utc))

            welcome_album.process_scheduled_jobs(datetime.datetime(2000, 01, 02, 0, 0, 0, tzinfo=utc))
            self.assertEqual(len(Album.objects.get_user_albums(self.bob.id)), 0)

            welcome_album.process_scheduled_jobs(datetime.datetime(2000, 01, 02, 0, 0, 0, tzinfo=utc) + WELCOME_ALBUM_DELAY - datetime.timedelta(seconds=1))
            self.assertEqual(len(Album.objects.get_user_albums(self.bob.id)), 0)

            welcome_album.process_scheduled_jobs(datetime.datetime(2000, 01, 02, 0, 0, 0, tzinfo=utc) + WELCOME_ALBUM_DELAY + datetime.timedelta(seconds=1))
            self.assertEqual(len(Album.objects.get_user_albums(self.bob.id)), 1)
            self.assertEqual(Album.objects.get_user_albums(self.bob.id)[0].creator, self.amanda)
            self.assertEqual(Album.objects.get_user_albums(self.bob.id)[0].name, 'Welcome')
