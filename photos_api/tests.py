import json

from django.contrib import auth
from django.test import TestCase
from django.utils import timezone

from photos.models import Album, Photo

class BaseTestCase(TestCase):
    fixtures = ['tests/test_users', 'tests/test_albums']
    urls = 'photos_api.urls'

class AnonymousTest(BaseTestCase):
    def verify_403(self, url):
        status = self.client.get(url).status_code
        self.assertEqual(status, 403)

    def test_albums(self):
        self.verify_403('/albums/')

    def test_album_detail(self):
        self.verify_403('/albums/1/')
        self.verify_403('/albums/2/')
        self.verify_403('/albums/3/')

        status = self.client.get('/albums/11/').status_code
        self.assertEqual(status, 404)

class UserTest(BaseTestCase):
    def setUp(self):
        self.client.login(username='amanda', password='amanda')

    def get_response_json(self, url):
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        return json.loads(response.content)

    def test_albums(self):
        all_albums = self.get_response_json('/albums/')
        self.assertEqual(len(all_albums), 5)

        first_album_url = all_albums[0]['url']
        first_album_response = self.client.get(first_album_url)
        self.assertEqual(first_album_response.status_code, 200)

class NotModifiedTest(BaseTestCase):
    def setUp(self):
        self.client.login(username='amanda', password='amanda')

    def test_single_album(self):
        # Get album 8
        first_response = self.client.get('/albums/8/')
        self.assertEqual(first_response.status_code, 200)
        etag = first_response['etag']

        # Get the same album again, it is unchanged, so it returns 304
        second_response = self.client.get('/albums/8/', HTTP_IF_NONE_MATCH=etag)
        self.assertEqual(second_response.status_code, 304)

        # Add a new photo to the album
        album = Album.objects.get(pk=8)
        barney = auth.get_user_model().objects.get(username='barney')
        photo_id = Photo.objects.upload_request(barney)
        Photo.objects.upload_to_album(photo_id, album, timezone.now())

        # Album is changed so server must return a full response
        third_response = self.client.get('/albums/8/', HTTP_IF_NONE_MATCH=etag)
        self.assertEqual(third_response.status_code, 200)
        self.assertNotEqual(etag, third_response['etag'])

    def test_all_albums(self):
        # Get all albums
        first_response = self.client.get('/albums/')
        self.assertEqual(first_response.status_code, 200)
        date = first_response['date']

        # Get all the albums again, none are changed, so it returns 304
        second_response = self.client.get('/albums/', HTTP_IF_MODIFIED_SINCE=date)
        self.assertEqual(second_response.status_code, 304)

        # Add a new photo to the album
        album = Album.objects.get(pk=8)
        barney = auth.get_user_model().objects.get(username='barney')
        photo_id = Photo.objects.upload_request(barney)
        Photo.objects.upload_to_album(photo_id, album, timezone.now())

        # An album is changed so server must return a full response
        third_response = self.client.get('/albums/', HTTP_IF_MODIFIED_SINCE=date)
        self.assertEqual(third_response.status_code, 200)
