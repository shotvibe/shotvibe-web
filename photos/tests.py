import datetime

from django.contrib import auth
from django.test import TestCase
from django.utils.timezone import utc
from django.test.utils import override_settings

from photos.models import Album, Photo, PendingPhoto
from photos import image_uploads

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

@override_settings(LOCAL_PHOTO_BUCKETS_BASE_PATH='.tmp_photo_buckets')
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

        location, directory = PendingPhoto.objects.get(photo_id=photo_id).bucket.split(':')
        if location != 'local':
            raise ValueError('Unknown photo bucket location: ' + location)

        with open('photos/test_photos/death-valley-sand-dunes.jpg') as f:
            image_uploads.handle_file_upload(directory, photo_id, read_in_chunks(f))

        new_photo = Photo.objects.upload_to_album(photo_id, album, the_date)

        self.assertFalse(PendingPhoto.objects.filter(photo_id=photo_id).exists())

        # This is the size of the test photo:
        self.assertEqual((new_photo.width, new_photo.height), (1024, 768))

        self.assertEqual(list(album.get_photos()), [new_photo])

    def test_album_last_updated_photo_upload(self):
        create_date = datetime.datetime(2010, 1, 1, tzinfo=utc)

        the_album = Album.objects.create_album(self.amanda, 'Ski Trip', create_date)
        self.assertEqual(the_album.last_updated, create_date)

        update_date = datetime.datetime(2010, 1, 2, tzinfo=utc)

        photo_id = Photo.objects.upload_request(self.amanda)

        location, directory = PendingPhoto.objects.get(photo_id=photo_id).bucket.split(':')
        if location != 'local':
            raise ValueError('Unknown photo bucket location: ' + location)

        with open('photos/test_photos/death-valley-sand-dunes.jpg') as f:
            image_uploads.handle_file_upload(directory, photo_id, read_in_chunks(f))

        Photo.objects.upload_to_album(photo_id, the_album, update_date)

        self.assertEqual(the_album.last_updated, update_date)

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
