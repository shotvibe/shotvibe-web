import json

from django.test import TestCase

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
        date = first_album_response['date']

        reload_album_response = self.client.get(first_album_url, HTTP_IF_MODIFIED_SINCE=date)
        self.assertEqual(reload_album_response.status_code, 304)
