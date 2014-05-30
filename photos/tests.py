import datetime
import shutil
from django.db.models.query import QuerySet

from django.conf import settings
from django.contrib import auth
from django.test import TestCase
from django.utils.timezone import utc
from django.test.utils import override_settings

import phonenumbers

from photos.models import Album, Photo, PendingPhoto, AlbumMember
from photos import image_uploads
from photos import photo_operations
from phone_auth.models import User, PhoneNumber

def read_in_chunks(file_object, chunk_size=1024):
    """
    Lazy function (generator) to read a file piece by piece.

    Default chunk size: 1024 bytes
    """
    while True:
        data = file_object.read(chunk_size)
        if not data:
            break
        yield data

@override_settings(USING_LOCAL_PHOTOS=True)
@override_settings(LOCAL_PHOTOS_DIRECTORY='.tmp_photos')
class ModelTest(TestCase):
    fixtures = ['tests/test_users']

    def setUp(self):
        self.amanda = auth.get_user_model().objects.get(pk=2)
        self.barney = auth.get_user_model().objects.get(pk=3)

    def tearDown(self):
        shutil.rmtree(settings.LOCAL_PHOTOS_DIRECTORY, ignore_errors=True)

    def test_issue_22(self):
        user_albums_qs = Album.objects.get_user_albums(self.amanda.pk)
        self.assertTrue(isinstance(user_albums_qs, QuerySet))

    def test_create_new_album(self):
        the_date = datetime.datetime(2010, 1, 1, tzinfo=utc)
        album = Album.objects.create_album(self.amanda, 'Ski Trip', the_date)

        self.assertTrue(album.is_user_member(self.amanda.id))
        self.assertFalse(album.is_user_member(self.barney.id))

        membership = AlbumMember.objects.filter(user=self.amanda, album=album).get()
        self.assertEqual(membership.added_by_user, self.amanda)

        self.assertEqual(list(Album.objects.get_user_albums(self.amanda.id)), [album])
        self.assertEqual(list(Album.objects.get_user_albums(self.barney.id)), [])

        pending_photo = Photo.objects.upload_request(author=self.amanda)

        with open('photos/test_photos/death-valley-sand-dunes.jpg') as f:
            image_uploads.process_file_upload(pending_photo, read_in_chunks(f))

        photo_operations.add_pending_photos_to_album([pending_photo.photo_id], album.id, the_date)

        self.assertFalse(PendingPhoto.objects.filter(photo_id=pending_photo.photo_id).exists())

        self.assertEqual(list(album.get_photos()), [Photo.objects.get(pk=pending_photo.photo_id)])

    def test_album_last_updated_photo_upload(self):
        create_date = datetime.datetime(2010, 1, 1, tzinfo=utc)

        the_album = Album.objects.create_album(self.amanda, 'Ski Trip', create_date)
        self.assertEqual(the_album.last_updated, create_date)

        update_date = datetime.datetime(2010, 1, 2, tzinfo=utc)

        pending_photo = Photo.objects.upload_request(author=self.amanda)

        with open('photos/test_photos/death-valley-sand-dunes.jpg') as f:
            image_uploads.process_file_upload(pending_photo, read_in_chunks(f))

        photo_operations.add_pending_photos_to_album([pending_photo.photo_id], the_album.id, update_date)

        # Refresh the_album to get the latest data from the DB
        the_album = Album.objects.get(pk=the_album.id)
        self.assertEqual(the_album.last_updated, update_date)

class AlbumTest(TestCase):
    def setUp(self):
        self.amanda = User.objects.create_user('amanda')

        self.barney = User.objects.create_user('barney')
        PhoneNumber.objects.create(
                phone_number = '+12127182003',
                user = self.barney,
                date_created = datetime.datetime(1999, 01, 01, tzinfo=utc),
                verified = True)

        self.party_album = Album.objects.create_album(self.amanda, 'Party', datetime.datetime(2000, 01, 01, tzinfo=utc))

    def test_add_invalid_user_id(self):
        the_time = datetime.datetime(2000, 01, 02, tzinfo=utc)

        with self.party_album.modify(the_time) as m:
            invalid_user_id = -1 # user ids are guaranteed to be positive
            result = m.add_user_id(self.amanda, invalid_user_id)
            self.assertFalse(result)

    def test_add_valid_user_id(self):
        the_time = datetime.datetime(2000, 01, 02, tzinfo=utc)

        before_revision_number = self.party_album.revision_number

        with self.party_album.modify(the_time) as m:
            result = m.add_user_id(self.amanda, self.barney.id)
            self.assertTrue(result)

        self.party_album = Album.objects.get(pk=self.party_album.pk)
        after_revision_number = self.party_album.revision_number

        self.assertGreater(after_revision_number, before_revision_number)

        self.assertTrue(self.party_album.is_user_member(self.barney.id))

    def test_add_existing_phone_number(self):
        the_time = datetime.datetime(2000, 01, 02, tzinfo=utc)

        before_revision_number = self.party_album.revision_number

        with self.party_album.modify(the_time) as m:
            barney_number = m.add_phone_number(self.amanda, phonenumbers.parse('+12127182003'), 'Barney Smith', None)
            self.assertEquals(barney_number, PhoneNumber.objects.get(user=self.barney))

        self.party_album = Album.objects.get(pk=self.party_album.pk)
        after_revision_number = self.party_album.revision_number

        self.assertGreater(after_revision_number, before_revision_number)

        self.assertTrue(self.party_album.is_user_member(self.barney.id))

    def test_add_new_phone_number(self):
        the_time = datetime.datetime(2000, 01, 02, tzinfo=utc)

        before_revision_number = self.party_album.revision_number

        with self.party_album.modify(the_time) as m:
            new_phone_number = m.add_phone_number(self.amanda, phonenumbers.parse('+12127182004'), 'Chloe Smith', None)

        self.party_album = Album.objects.get(pk=self.party_album.pk)
        after_revision_number = self.party_album.revision_number

        self.assertGreater(after_revision_number, before_revision_number)

        self.assertEquals(new_phone_number.phone_number, '+12127182004')
        self.assertEquals(new_phone_number.user.nickname, 'Chloe Smith')
        self.assertTrue(self.party_album.is_user_member(new_phone_number.user.id))


class ImageUploads(TestCase):
    def test_box_fit_expanded(self):
        self.assertEqual(image_uploads.BoxFitExpanded(75, 75).get_image_dimensions(640, 480), (100, 75))
        self.assertEqual(image_uploads.BoxFitExpanded(75, 75).get_image_dimensions(480, 640), (75, 100))

    def test_box_fit_with_rotation(self):
        self.assertEqual(image_uploads.BoxFitWithRotation(480, 320).get_image_dimensions(640, 480), (426, 320))
        self.assertEqual(image_uploads.BoxFitWithRotation(480, 320).get_image_dimensions(480, 640), (320, 426))
        self.assertEqual(image_uploads.BoxFitWithRotation(480, 320).get_image_dimensions(320, 240), (426, 320))
        self.assertEqual(image_uploads.BoxFitWithRotation(480, 320).get_image_dimensions(320, 240), (426, 320))
        self.assertEqual(image_uploads.BoxFitWithRotation(480, 320).get_image_dimensions(1200, 1941), (296, 480))
        self.assertEqual(image_uploads.BoxFitWithRotation(480, 320).get_image_dimensions(1941, 1200), (480, 296))
        self.assertEqual(image_uploads.BoxFitWithRotation(960, 640).get_image_dimensions(1200, 1941), (593, 960))
        self.assertEqual(image_uploads.BoxFitWithRotation(960, 640).get_image_dimensions(1941, 1200), (960, 593))
        self.assertEqual(image_uploads.BoxFitWithRotation(1136, 640).get_image_dimensions(1200, 1941), (640, 1035))
        self.assertEqual(image_uploads.BoxFitWithRotation(1136, 640).get_image_dimensions(1941, 1200), (1035, 640))


    def test_box_fit_with_rotation_only_shrink(self):
        self.assertEqual(image_uploads.BoxFitWithRotationOnlyShrink(480, 320).get_image_dimensions(640, 480), (426, 320))
        self.assertEqual(image_uploads.BoxFitWithRotationOnlyShrink(480, 320).get_image_dimensions(480, 640), (320, 426))
        self.assertEqual(image_uploads.BoxFitWithRotationOnlyShrink(480, 320).get_image_dimensions(320, 240), (320, 240))
        self.assertEqual(image_uploads.BoxFitWithRotationOnlyShrink(480, 320).get_image_dimensions(320, 240), (320, 240))
        self.assertEqual(image_uploads.BoxFitWithRotationOnlyShrink(960, 640).get_image_dimensions(1024, 768), (853, 640))
        self.assertEqual(image_uploads.BoxFitWithRotationOnlyShrink(960, 640).get_image_dimensions(1024, 768), (853, 640))
        self.assertEqual(image_uploads.BoxFitWithRotationOnlyShrink(1136, 640).get_image_dimensions(1024, 768), (853, 640))
        self.assertEqual(image_uploads.BoxFitWithRotationOnlyShrink(1136, 640).get_image_dimensions(1024, 768), (853, 640))
