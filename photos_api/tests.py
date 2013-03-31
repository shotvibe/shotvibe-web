import filecmp
import json
import os
import shutil

from django.conf import settings
from django.test import TestCase
from django.test.utils import override_settings

from photos.models import PendingPhoto

from photos_api.serializers import AlbumUpdateSerializer, MemberIdentifier, MemberIdentifierSerializer, AlbumAddSerializer

@override_settings(LOCAL_PHOTO_BUCKETS_BASE_PATH='.tmp_photo_buckets')
class BaseTestCase(TestCase):
    fixtures = ['tests/test_users', 'tests/test_albums']
    urls = 'photos_api.urls'

class AnonymousTest(BaseTestCase):
    def verify_401(self, url):
        status = self.client.get(url).status_code
        self.assertEqual(status, 401)

    def test_albums(self):
        self.verify_401('/albums/')

    def test_album_detail(self):
        self.verify_401('/albums/1/')
        self.verify_401('/albums/2/')
        self.verify_401('/albums/3/')

        status = self.client.get('/albums/11/').status_code
        self.assertEqual(status, 404)

class UserTest(BaseTestCase):
    def setUp(self):
        self.client.login(username='2', password='amanda')

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
        self.client.login(username='2', password='amanda')

    def test_single_album(self):
        # Get album 8
        first_response = self.client.get('/albums/8/')
        self.assertEqual(first_response.status_code, 200)
        etag = first_response['etag']

        # Get the same album again, it is unchanged, so it returns 304
        second_response = self.client.get('/albums/8/', HTTP_IF_NONE_MATCH=etag)
        self.assertEqual(second_response.status_code, 304)

        # Add a new photo to the album
        upload_request_response = self.client.post('/photos/upload_request/')
        upload_request_json = json.loads(upload_request_response.content)

        photo_id = upload_request_json[0]['photo_id']
        upload_url = upload_request_json[0]['upload_url']

        test_photo_path = 'photos/test_photos/death-valley-sand-dunes.jpg'

        with open(test_photo_path, 'rb') as f:
            self.client.post(upload_url, { 'photo': f })

        photo_list = { 'add_photos': [ { 'photo_id': photo_id } ] }
        self.client.post('/albums/8/', content_type='application/json', data=json.dumps(photo_list))

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
        upload_request_response = self.client.post('/photos/upload_request/')
        upload_request_json = json.loads(upload_request_response.content)

        photo_id = upload_request_json[0]['photo_id']
        upload_url = upload_request_json[0]['upload_url']

        test_photo_path = 'photos/test_photos/death-valley-sand-dunes.jpg'

        with open(test_photo_path, 'rb') as f:
            self.client.post(upload_url, { 'photo': f })

        photo_list = { 'add_photos': [ { 'photo_id': photo_id } ] }
        self.client.post('/albums/8/', content_type='application/json', data=json.dumps(photo_list))

        # An album is changed so server must return a full response
        third_response = self.client.get('/albums/', HTTP_IF_MODIFIED_SINCE=date)
        self.assertEqual(third_response.status_code, 200)

class Serializers(TestCase):
    def test_album_update(self):
        test_data = { 'add_photos': [
            { 'photo_id': 'test_photo_1' },
            { 'photo_id': 'test_photo_2' }
            ] }
        serializer = AlbumUpdateSerializer(data=test_data)
        if not serializer.is_valid():
            self.fail(serializer.errors)
        self.assertEqual(serializer.object.add_photos, ['test_photo_1', 'test_photo_2'])

    def test_member_identifier_user_id(self):
        test_data = {
                'user_id': 3
                }
        serializer = MemberIdentifierSerializer(data=test_data)
        if not serializer.is_valid():
            self.fail(serializer.errors)
        self.assertEqual(serializer.object, MemberIdentifier(user_id=3))

    def test_member_identifier_phone_number(self):
        test_data = {
                'phone_number': '212-718-9999',
                'default_country': 'US'
                }
        serializer = MemberIdentifierSerializer(data=test_data)
        if not serializer.is_valid():
            self.fail(serializer.errors)
        self.assertEqual(serializer.object, MemberIdentifier(phone_number='212-718-9999', default_country='US'))

    def test_album_add(self):
        test_data = {
                'album_name': 'My New Album',
                'members': [
                    { 'user_id': 3 },
                    { 'user_id': 4 },
                    {
                        'phone_number': '212-718-9999',
                        'default_country': 'US' }
                    ],
                'photos': [
                    { 'photo_id': 'test_photo_1' },
                    { 'photo_id': 'test_photo_2' }
                    ]
                }
        serializer = AlbumAddSerializer(data=test_data)
        if not serializer.is_valid():
            self.fail(serializer.errors)
        self.assertEqual(serializer.object.album_name, 'My New Album')
        self.assertEqual(serializer.object.members, [
            MemberIdentifier(user_id=3),
            MemberIdentifier(user_id=4),
            MemberIdentifier(phone_number='212-718-9999', default_country='US')
            ])
        self.assertEqual(serializer.object.photos, ['test_photo_1', 'test_photo_2'])

class PhotoUpload(BaseTestCase):
    def setUp(self):
        self.client.login(username='2', password='amanda')

    def tearDown(self):
        shutil.rmtree(settings.LOCAL_PHOTO_BUCKETS_BASE_PATH, ignore_errors=True)

    def test_upload_single_post(self):
        upload_request_response = self.client.post('/photos/upload_request/')
        self.assertEqual(upload_request_response.status_code, 200)
        upload_request_json = json.loads(upload_request_response.content)

        photo_id = upload_request_json[0]['photo_id']
        upload_url = upload_request_json[0]['upload_url']

        test_photo_path = 'photos/test_photos/death-valley-sand-dunes.jpg'

        with open(test_photo_path, 'rb') as f:
            upload_response = self.client.post(upload_url, { 'photo': f })

        self.assertEqual(upload_response.status_code, 200)

        photo_pending = PendingPhoto.objects.get(pk=photo_id)
        directory = photo_pending.bucket.split(':')[1]
        uploaded_photo_path = os.path.join(settings.LOCAL_PHOTO_BUCKETS_BASE_PATH, directory, photo_id + '.jpg')
        self.assertTrue(filecmp.cmp(test_photo_path, uploaded_photo_path, shallow=False))

    def test_upload_single_put(self):
        upload_request_response = self.client.post('/photos/upload_request/')
        self.assertEqual(upload_request_response.status_code, 200)
        upload_request_json = json.loads(upload_request_response.content)

        photo_id = upload_request_json[0]['photo_id']
        upload_url = upload_request_json[0]['upload_url']

        test_photo_path = 'photos/test_photos/death-valley-sand-dunes.jpg'

        with open(test_photo_path, 'rb') as f:
            upload_response = self.client.put(upload_url, f.read(), 'application/octet-stream')

        self.assertEqual(upload_response.status_code, 200)

        photo_pending = PendingPhoto.objects.get(pk=photo_id)
        directory = photo_pending.bucket.split(':')[1]
        uploaded_photo_path = os.path.join(settings.LOCAL_PHOTO_BUCKETS_BASE_PATH, directory, photo_id + '.jpg')
        self.assertTrue(filecmp.cmp(test_photo_path, uploaded_photo_path, shallow=False))

    def test_add_to_album(self):
        upload_request_response = self.client.post('/photos/upload_request/')
        self.assertEqual(upload_request_response.status_code, 200)
        upload_request_json = json.loads(upload_request_response.content)

        photo_id = upload_request_json[0]['photo_id']
        upload_url = upload_request_json[0]['upload_url']

        test_photo_path = 'photos/test_photos/death-valley-sand-dunes.jpg'

        with open(test_photo_path, 'rb') as f:
            upload_response = self.client.post(upload_url, { 'photo': f })
        self.assertEqual(upload_response.status_code, 200)

        num_photos_before = len(json.loads(self.client.get('/albums/8/').content)['photos'])

        photo_list = { 'add_photos': [ { 'photo_id': photo_id } ] }
        add_response = self.client.post('/albums/8/', content_type='application/json', data=json.dumps(photo_list))
        self.assertEqual(add_response.status_code, 200)

        album_json = json.loads(self.client.get('/albums/8/').content)
        num_photos_after = len(album_json['photos'])
        self.assertEqual(num_photos_after, num_photos_before + 1)

        all_album_photos = [x['photo_id'] for x in album_json['photos']]
        self.assertIn(photo_id, all_album_photos)

    def test_create_album(self):
        upload_request_response = self.client.post('/photos/upload_request/')
        self.assertEqual(upload_request_response.status_code, 200)
        upload_request_json = json.loads(upload_request_response.content)

        photo_id = upload_request_json[0]['photo_id']
        upload_url = upload_request_json[0]['upload_url']

        test_photo_path = 'photos/test_photos/death-valley-sand-dunes.jpg'

        with open(test_photo_path, 'rb') as f:
            upload_response = self.client.post(upload_url, { 'photo': f })
        self.assertEqual(upload_response.status_code, 200)

        members = [ { 'user_id': 3 } ] # barney

        new_album_data = {
                'album_name': 'My New Album',
                'members': members,
                'photos': [
                    { 'photo_id': photo_id }
                    ]
                }

        create_response = self.client.post('/albums/', content_type='application/json', data=json.dumps(new_album_data), follow=True)
        self.assertEqual(create_response.status_code, 200)

        album_json = json.loads(create_response.content)
        self.assertEqual(album_json['name'], 'My New Album')
        self.assertEqual(len(album_json['photos']), 1)
        self.assertEqual(album_json['photos'][0]['photo_id'], photo_id)
        self.assertEqual(len(album_json['members']), 2)
        members_ids = [u['id'] for u in album_json['members']]
        self.assertIn(2, members_ids) # amanda
        self.assertIn(3, members_ids) # barney

    def test_create_empty_album(self):
        new_album_data = {
                'album_name': 'My New Album',
                'members': [],
                'photos': []
                }

        create_response = self.client.post('/albums/', content_type='application/json', data=json.dumps(new_album_data), follow=True)
        self.assertEqual(create_response.status_code, 200)

        album_json = json.loads(create_response.content)
        self.assertEqual(album_json['name'], 'My New Album')
        self.assertEqual(len(album_json['photos']), 0)
        self.assertEqual(len(album_json['members']), 1)
        members_ids = [u['id'] for u in album_json['members']]
        self.assertIn(2, members_ids) # amanda

class MembersTests(BaseTestCase):
    def setUp(self):
        self.client.login(username='2', password='amanda')

    def test_add_members(self):
        album_before_response = self.client.get('/albums/9/')
        members_before = json.loads(album_before_response.content)['members']
        etag = album_before_response['etag']

        add_members = { 'add_members': [
            { 'user_id': 3 },
            { 'user_id': 4 },
            { 'user_id': 12 }
            ] }

        add_response = self.client.post('/albums/9/', content_type='application/json', data=json.dumps(add_members))
        self.assertEqual(add_response.status_code, 200)

        album_after_response = self.client.get('/albums/9/', HTTP_IF_NONE_MATCH=etag)
        self.assertEqual(album_after_response.status_code, 200)

        members_after = json.loads(album_after_response.content)['members']

        members_ids_before = [u['id'] for u in members_before]
        members_ids_after = [u['id'] for u in members_after]
        self.assertEqual(set(members_ids_before + [3, 4, 12]), set(members_ids_after))
