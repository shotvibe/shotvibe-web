import datetime
import filecmp
import httplib
import json
import phonenumbers
from boto.s3.connection import S3Connection
from boto.s3.key import Key
from django.core.urlresolvers import reverse
import os
import shutil

from django.conf import settings
from django.conf.urls import patterns, include, url
from django.contrib import auth
from django.test import TestCase, Client
from django.test.utils import override_settings
from django.utils import timezone

from phone_auth.models import AuthToken
from phone_auth.models import PhoneNumber, PhoneContact, AnonymousPhoneNumber, PhoneNumberLinkCode
from phone_auth.sms_send import send_sms, mark_sms_test_case
from photos.models import Photo, PendingPhoto, Album, AlbumMember, PhotoGlance, PhotoComment
from photos_api import is_phone_number_mobile
from invites_manager.models import SMSInviteMessage
import invites_manager
import frontend.urls
import photos_api.urls

from photos_api.serializers import AlbumUpdateSerializer, MemberIdentifier, MemberIdentifierSerializer, AlbumAddSerializer
import requests

try:
    from django.contrib.auth import get_user_model
except ImportError:
    from django.contrib.auth.models import User
else:
    User = get_user_model()


@override_settings(USING_LOCAL_PHOTOS=True)
@override_settings(LOCAL_PHOTOS_DIRECTORY='.tmp_photos')
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

    def test_avatar_upload(self):
        # ===================================
        # Create data needed to test AnonymousPhoneNumber.avatar_file sync
        amanda = User.objects.get(nickname='amanda')
        fred = User.objects.get(nickname='fred')
        apn = AnonymousPhoneNumber.objects.create(
            phone_number='+12127189999',
            is_mobile=True,
            is_mobile_queried=timezone.now()
        )
        phone_contact = PhoneContact.objects.create(
            anonymous_phone_number=apn,
            user=amanda,
            created_by_user=fred,
            date_created=timezone.now(),
            contact_nickname='amanda1'
        )
        initial_avatar=apn.avatar_file
        # ===================================


        test_avatar_path = 'photos/test_photos/death-valley-sand-dunes.jpg'
        url = reverse('user-avatar', kwargs={'pk': 2})

        with open(test_avatar_path, 'rb') as f:
            upload_response = self.client.put(url, f.read(),
                                              'application/octet-stream')
        self.assertEqual(upload_response.status_code, 200)
        user = auth.get_user_model().objects.get(id=2)
        self.assertTrue(user.avatar_file.startswith("s3:"))

        response = requests.get(user.get_avatar_url())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['content-type'], "image/jpeg")

        # Test that avatar for AnonymousPhoneNumber was changed as well
        new_apn = AnonymousPhoneNumber.objects.get(pk=apn.pk)
        self.assertEqual(user.avatar_file,
                         new_apn.avatar_file)

        storage, bucket_name, filename = user.avatar_file.split(":")

        # Delete test image from S3
        if storage == 's3':
            conn = S3Connection(settings.AWS_ACCESS_KEY,
                                settings.AWS_SECRET_ACCESS_KEY)
            bucket = conn.get_bucket(bucket_name)
            key = Key(bucket, filename)
            key.delete()
            key.close(fast=True)

    def test_user_updates(self):
        logged_in_user_id = 2
        initial_user = get_user_model().objects.get(pk=logged_in_user_id)
        data = {'nickname': 'testnickname'}
        user_url = reverse('user-detail', kwargs={'pk': logged_in_user_id})
        response = self.client.post(user_url, data, REQUEST_METHOD=str('PATCH'))
        self.assertEqual(response.status_code, httplib.OK)
        updated_user = get_user_model().objects.get(pk=logged_in_user_id)
        self.assertEqual(updated_user.nickname, data['nickname'])

        # Test disallowed attrs
        disallowed_attrs = {
            'id': 23423423,
            'primary_email': 'ingo@shotvibe.com',
            'date_joined': timezone.now(),
            'is_registered': not initial_user.is_registered,
            'is_staff': not initial_user.is_staff,
            'is_active': not initial_user.is_active,
            'avatar_file': 'test-file.jpg'
        }
        for attr_name, value in disallowed_attrs.iteritems():
            data = {attr_name: value}
            response = self.client.post(user_url, data,
                                        REQUEST_METHOD=str('PATCH'))

            self.assertEqual(response.status_code, httplib.FORBIDDEN)
            updated_user = get_user_model().objects.get(pk=logged_in_user_id)
            self.assertNotEqual(getattr(updated_user, attr_name),
                                data[attr_name])

    def test_query_phone_numbers_auth(self):
        client = Client()
        response = client.post(
            reverse('query-phone-numbers'),
            {'default_acountry': 'US', 'phone_numbers': []}
        )
        self.assertEqual(response.status_code, httplib.UNAUTHORIZED)

    def test_query_phone_numbers_invalid(self):
        data = {
            "default_country": "us",
            "phone_numbers": [
                {
                    "phone_number": "212718999923123123",
                    "contact_nickname": "John Smith"
                },
            ]
        }
        response = self.client.post(reverse('query-phone-numbers'),
                                    json.dumps(data, indent=4),
                                    content_type="application/json")
        self.assertEqual(response.status_code, httplib.OK)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['phone_number_details'][0],
                         {'phone_type': 'invalid'})

    def test_query_phone_numbers_unknown(self):

        # make sure we don't have this phone number
        self.assertRaises(PhoneNumber.DoesNotExist, PhoneNumber.objects.get,
                          phone_number='+12127189999')

        data = {
            "default_country": "us",
            "phone_numbers": [
                {
                    "phone_number": "2127189999",
                    "contact_nickname": "John Smith"
                },
            ]
        }
        response = self.client.post(reverse('query-phone-numbers'),
                                    json.dumps(data, indent=4),
                                    content_type="application/json")
        self.assertEqual(response.status_code, httplib.OK)
        response_data = json.loads(response.content)
        phone_numbers = response_data['phone_number_details']
        self.assertEqual(phone_numbers[0]['user_id'], None)
        initial_avatar = phone_numbers[0]['avatar_url']


        # Make request from different user and with the same anonymous phone
        # number and make sure the same avatar is used.
        client = Client()
        client.login(username=3, password="barney")
        response = client.post(reverse('query-phone-numbers'),
                               json.dumps(data, indent=4),
                               content_type='application/json')
        self.assertEqual(response.status_code, httplib.OK)
        response_data = json.loads(response.content)
        phone_numbers = response_data['phone_number_details']
        self.assertEqual(phone_numbers[0]['user_id'], None)
        self.assertEqual(phone_numbers[0]['avatar_url'], initial_avatar)

    def test_query_phone_numbers_existing(self):

        amanda = User.objects.get(nickname='amanda')
        fred = User.objects.get(nickname='fred')
        phone_number = PhoneNumber.objects.create(
            phone_number='+12127189999',
            user=fred,
            date_created=timezone.now(),
            verified=True
        )

        data = {
            "default_country": "us",
            "phone_numbers": [
                {
                    "phone_number": "2127189999",
                    "contact_nickname": "John Smith"
                },
            ]
        }
        response = self.client.post(reverse('query-phone-numbers'),
                                    json.dumps(data, indent=4),
                                    content_type="application/json")
        self.assertEqual(response.status_code, httplib.OK)
        response_data = json.loads(response.content)
        phone_numbers = response_data['phone_number_details']
        self.assertEqual(phone_numbers[0]['user_id'], fred.id)
        initial_avatar = phone_numbers[0]['avatar_url']


        # Make request from different user and with the same anonymous phone
        # number and make sure the same avatar is used.
        client = Client()
        client.login(username=3, password="barney")
        response = client.post(reverse('query-phone-numbers'),
                               json.dumps(data, indent=4),
                               content_type='application/json')
        self.assertEqual(response.status_code, httplib.OK)
        response_data = json.loads(response.content)
        phone_numbers = response_data['phone_number_details']
        self.assertEqual(phone_numbers[0]['user_id'], fred.id)
        self.assertEqual(phone_numbers[0]['avatar_url'], initial_avatar)

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

    def test_last_access(self):
        # Get all albums
        first_response = self.client.get('/albums/')
        self.assertEqual(first_response.status_code, 200)

        # Should have 3 new photos
        album = self.get_album(first_response, 8)
        self.assertEqual(album['num_new_photos'], 3)

        # mark album 8 as seen
        data = json.dumps({"timestamp": timezone.now().isoformat()})
        view_response = self.client.post('/albums/8/view/', content_type='application/json', data=data)
        self.assertEqual(view_response.status_code, 204)

        # Get albums list again
        second_response = self.client.get('/albums/')
        self.assertEqual(first_response.status_code, 200)

        # No new photos
        album = self.get_album(second_response, 8)
        self.assertEqual(album['num_new_photos'], 0)

        # Add a new photo to the album
        self.add_new_photo('3', 'barney')

        third_response = self.client.get('/albums/')
        self.assertEqual(third_response.status_code, 200)

        # One new photo
        album = self.get_album(third_response, 8)
        self.assertEqual(album['num_new_photos'], 1)

        # Same user adding a photo
        self.add_new_photo('2', 'amanda')

        # Still one photo (barney's)
        fourth_response = self.client.get('/albums/8/')
        self.assertEqual(fourth_response.status_code, 200)
        fourth_response_json = json.loads(fourth_response.content)
        self.assertEqual(1, fourth_response_json['num_new_photos'])

    def add_new_photo(self, username, password):
        self.client.login(username=username, password=password)

        upload_request_response = self.client.post('/photos/upload_request/')
        upload_request_json = json.loads(upload_request_response.content)

        photo_id = upload_request_json[0]['photo_id']
        upload_url = upload_request_json[0]['upload_url']

        test_photo_path = 'photos/test_photos/death-valley-sand-dunes.jpg'

        with open(test_photo_path, 'rb') as f:
            self.client.post(upload_url, { 'photo': f })

        photo_list = { 'add_photos': [ { 'photo_id': photo_id } ] }
        self.client.post('/albums/8/', content_type='application/json', data=json.dumps(photo_list))

        self.client.login(username='2', password='amanda')

    def get_album(self, response, aid):
        for album in json.loads(response.content):
            if album['id'] == aid:
                return album


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
                'user_id': 3,
                }
        serializer = MemberIdentifierSerializer(data=test_data)
        if not serializer.is_valid():
            self.fail(serializer.errors)
        self.assertEqual(serializer.object, MemberIdentifier(user_id=3))

    def test_member_identifier_phone_number(self):
        test_data = {
                'phone_number': '212-718-9999',
                'default_country': 'US',
                'contact_nickname':'qwer'
                }
        serializer = MemberIdentifierSerializer(data=test_data)
        if not serializer.is_valid():
            self.fail(serializer.errors)
        expected_member = MemberIdentifier(phone_number='212-718-9999', default_country='US', contact_nickname='qwer')
        self.assertEqual(serializer.object, expected_member)

    def test_member_identifier_required_nickname(self):
        test_data = {
            'phone_number': '212-718-9999',
            'default_country': 'US',
        }
        serializer = MemberIdentifierSerializer(data=test_data)
        self.assertFalse(serializer.is_valid())
        self.assertTrue('non_field_errors' in serializer._errors)
        self.assertEqual(
            unicode(serializer.fields['contact_nickname'].error_messages.get('required_with_phone_number')),
            str(serializer._errors['non_field_errors'][0])
        )

    def test_album_add(self):
        test_data = {
                'album_name': 'My New Album',
                'members': [
                    { 'user_id': 3 },
                    { 'user_id': 4 },
                    {
                        'phone_number': '212-718-9999',
                        'default_country': 'US',
                        'contact_nickname': 'John Smith' }
                    ]
                }
        serializer = AlbumAddSerializer(data=test_data)
        if not serializer.is_valid():
            self.fail(serializer.errors)
        self.assertEqual(serializer.object.album_name, 'My New Album')
        self.assertEqual(serializer.object.members, [
            MemberIdentifier(user_id=3),
            MemberIdentifier(user_id=4),
            MemberIdentifier(phone_number='212-718-9999', default_country='US', contact_nickname='John Smith')
            ])


class PhotoTests(BaseTestCase):

    def setUp(self):
        self.client.login(username='2', password='amanda')

    def tearDown(self):
        shutil.rmtree(settings.LOCAL_PHOTOS_DIRECTORY, ignore_errors=True)

    def upload_and_add_photo_to_album(self, album_id, client=None):
        if not client:
            client = self.client
        album_url = reverse('album-detail', kwargs={'pk': album_id})
        upload_request_response = client.post(
            reverse('photos-upload-request'))
        upload_request_json = json.loads(upload_request_response.content)

        photo_id = upload_request_json[0]['photo_id']
        upload_url = upload_request_json[0]['upload_url']

        test_photo_path = 'photos/test_photos/death-valley-sand-dunes.jpg'

        with open(test_photo_path, 'rb') as f:
            upload_response = client.post(upload_url, {'photo': f})

        photo_list = {'add_photos': [{'photo_id': photo_id}]}
        add_response = client.post(album_url,
                                   content_type='application/json',
                                   data=json.dumps(photo_list))
        return photo_id

    def test_delete_photos(self):

        album_url = reverse('album-detail', kwargs={'pk': 9})
        album_before_response = self.client.get(album_url)

        # Upload and add photo to the album
        photo_id = self.upload_and_add_photo_to_album(9)

        # Upload one more photo from other user
        daniel = Client()
        daniel.login(username="5", password="daniel")
        daniel_photo_id = self.upload_and_add_photo_to_album(9, client=daniel)

        # Test that photo was successfully added
        album_json = json.loads(self.client.get(album_url).content)
        all_album_photos = [x['photo_id'] for x in album_json['photos']]
        self.assertIn(photo_id, all_album_photos)
        self.assertIn(daniel_photo_id, all_album_photos)

        # Delete photo
        url = reverse('photos-delete')
        data = {'photos': [
            {'photo_id': photo_id},
        ]}
        response = self.client.post(url,
                                    content_type='application/json',
                                    data=json.dumps(data))

        # Test that photo is not in album anymore
        album_json = json.loads(self.client.get(album_url).content)
        all_album_photos = [x['photo_id'] for x in album_json['photos']]
        self.assertNotIn(photo_id, all_album_photos)
        self.assertIn(daniel_photo_id, all_album_photos)


class PhotoUpload(BaseTestCase):
    def setUp(self):
        self.client.login(username='2', password='amanda')

    def tearDown(self):
        shutil.rmtree(settings.LOCAL_PHOTOS_DIRECTORY, ignore_errors=True)

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
        storage_id = photo_pending.storage_id
        uploaded_photo_path = os.path.join(settings.LOCAL_PHOTOS_DIRECTORY, storage_id + '.jpg')
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
        storage_id = photo_pending.storage_id
        uploaded_photo_path = os.path.join(settings.LOCAL_PHOTOS_DIRECTORY, storage_id + '.jpg')
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
                'members': members
                }

        create_response = self.client.post('/albums/', content_type='application/json', data=json.dumps(new_album_data))
        self.assertEqual(create_response.status_code, 200)

        album_json = json.loads(create_response.content)
        self.assertEqual(album_json['name'], 'My New Album')
        self.assertEqual(len(album_json['members']), 2)
        members_ids = [u['id'] for u in album_json['members']]
        self.assertIn(2, members_ids) # amanda
        self.assertIn(3, members_ids) # barney
        self.assertEqual(album_json['num_new_photos'], 0)
        self.assertEqual(album_json['last_access'], None)

    def test_create_empty_album(self):
        new_album_data = {
                'album_name': 'My New Album',
                'members': [],
                'photos': []
                }

        create_response = self.client.post('/albums/', content_type='application/json', data=json.dumps(new_album_data))
        self.assertEqual(create_response.status_code, 200)

        album_json = json.loads(create_response.content)
        self.assertEqual(album_json['name'], 'My New Album')
        self.assertEqual(len(album_json['photos']), 0)
        self.assertEqual(len(album_json['members']), 1)
        members_ids = [u['id'] for u in album_json['members']]
        self.assertIn(2, members_ids) # amanda


class PhotoCommentsTest(TestCase):
    urls = 'photos_api.urls'

    def setUp(self):
        self.arnold = User.objects.create_user('arnold', password='mypass')
        self.party_album = Album.objects.create_album(self.arnold, 'Party', datetime.datetime(2000, 1, 1, tzinfo=timezone.utc))

        Photo.objects.create(
                photo_id = 'test-photo-id-1',
                storage_id = 'test-storage-id-1',
                subdomain = 'test-subdomain',
                date_created = datetime.datetime(2000, 1, 2, tzinfo=timezone.utc),
                author = self.arnold,
                album = self.party_album,
                album_index = 0)

        self.client.login(username=str(self.arnold.id), password='mypass')

    def test_comment_photo(self):
        data = {
                'comment': 'Hi, this is a test comment!'
                }
        response = self.client.put(
                reverse('photo-comment', kwargs={
                    'photo_id': 'test-photo-id-1',
                    'client_msg_id': '123000000000' }),
                data = json.dumps(data),
                content_type = 'application/json')
        self.assertEqual(response.status_code, 204)

        photo_comment = PhotoComment.objects.get(photo__photo_id='test-photo-id-1', author=self.arnold)
        self.assertEqual(photo_comment.comment_text, 'Hi, this is a test comment!')
        self.assertEqual(photo_comment.client_msg_id, 123000000000)


class PhotoGlanceTest(TestCase):
    urls = 'photos_api.urls'

    def setUp(self):
        self.arnold = User.objects.create_user('arnold', password='mypass')
        self.party_album = Album.objects.create_album(self.arnold, 'Party', datetime.datetime(2000, 1, 1, tzinfo=timezone.utc))

        Photo.objects.create(
                photo_id = 'test-photo-id-1',
                storage_id = 'test-storage-id-1',
                subdomain = 'test-subdomain',
                date_created = datetime.datetime(2000, 1, 2, tzinfo=timezone.utc),
                author = self.arnold,
                album = self.party_album,
                album_index = 0)

        self.client.login(username=str(self.arnold.id), password='mypass')

    def test_glance_photo(self):
        data = {
                'emoticon_name': 'test-smile'
                }
        response = self.client.put(
                reverse('photo-glance', kwargs={'photo_id':'test-photo-id-1'}),
                data = json.dumps(data),
                content_type = 'application/json')
        self.assertEqual(response.status_code, 204)

        photo_glance = PhotoGlance.objects.get(photo__photo_id='test-photo-id-1', author=self.arnold)
        self.assertEqual(photo_glance.emoticon_name, 'test-smile')

    def test_glance_photo_multiple(self):
        data1 = {
                'emoticon_name': 'test-smile-1'
                }
        response = self.client.put(
                reverse('photo-glance', kwargs={'photo_id':'test-photo-id-1'}),
                data = json.dumps(data1),
                content_type = 'application/json')
        self.assertEqual(response.status_code, 204)

        data2 = {
                'emoticon_name': 'test-smile-2'
                }
        response = self.client.put(
                reverse('photo-glance', kwargs={'photo_id':'test-photo-id-1'}),
                data = json.dumps(data2),
                content_type = 'application/json')
        self.assertEqual(response.status_code, 204)

        photo_glance = PhotoGlance.objects.get(photo__photo_id='test-photo-id-1', author=self.arnold)
        self.assertEqual(photo_glance.emoticon_name, 'test-smile-2')

    def test_glance_view(self):
        blake = User.objects.create_user('blake')

        PhotoGlance.objects.create(
                photo = Photo.objects.get(photo_id='test-photo-id-1'),
                emoticon_name = 'test-smile',
                date_created = datetime.datetime(2000, 1, 3, tzinfo=timezone.utc),
                author = self.arnold)

        PhotoGlance.objects.create(
                photo = Photo.objects.get(photo_id='test-photo-id-1'),
                emoticon_name = 'test-wink',
                date_created = datetime.datetime(2000, 1, 4, tzinfo=timezone.utc),
                author = blake)

        response = self.client.get(reverse('album-detail', kwargs={'pk': str(self.party_album.id)}))
        self.assertEqual(response.status_code, 200)
        j = json.loads(response.content)

        self.assertEqual(j['photos'][0]['glances'][0]['emoticon_name'], 'test-smile')
        self.assertEqual(j['photos'][0]['glances'][0]['author']['id'], self.arnold.id)

        self.assertEqual(j['photos'][0]['glances'][1]['emoticon_name'], 'test-wink')
        self.assertEqual(j['photos'][0]['glances'][1]['author']['id'], blake.id)


class AlbumNameTest(BaseTestCase):
    def setUp(self):
        self.client.login(username='2', password='amanda')

    def test_get_invalid_album_name(self):
        name_response = self.client.get('/albums/0/name/')
        self.assertEqual(name_response.status_code, 404)

    def test_get_album_name(self):
        name_response = self.client.get('/albums/9/name/')
        self.assertEqual(name_response.status_code, 200)
        j = json.loads(name_response.content)
        self.assertEqual(j['name'], 'cautioned whoa')

    def test_invalid_permission_set_album_name(self):
        change_name = {
                'name': 'My New Album Name'
                }
        set_response = self.client.put('/albums/9/name/', data=json.dumps(change_name))
        self.assertEqual(set_response.status_code, httplib.FORBIDDEN)

    def test_set_album_name(self):
        client = Client()
        client.login(username='11', password='jackie')
        change_name = {
                'name': 'My New Album Name'
                }
        set_response = client.put(
                '/albums/9/name/',
                data=json.dumps(change_name),
                content_type='application/json')
        self.assertEqual(set_response.status_code, 204)

        self.assertEqual(Album.objects.get(pk=9).name, 'My New Album Name')


class MembersTests(BaseTestCase):
    def setUp(self):
        try:
            d = SMSInviteMessage.objects.get(
                    country_calling_code = SMSInviteMessage.COUNTRY_DEFAULT_VALUE,
                    time_delay_hours = 0)
            d.message_template = 'Hi ${name}. ${inviter} shared an album: ${album}'
            d.save(update_fields=['message_template'])
        except SMSInviteMessage.DoesNotExist:
            d = SMSInviteMessage.objects.create(
                    country_calling_code = SMSInviteMessage.COUNTRY_DEFAULT_VALUE,
                    time_delay_hours = 0,
                    message_template = 'Hi ${name}. ${inviter} shared an album: ${album}')

        self.client.login(username='2', password='amanda')

    def test_invite_status(self):
        album_url = reverse('album-detail', kwargs={'pk': 9})
        album_before_response = self.client.get(album_url)
        j = json.loads(album_before_response.content)
        for member in j['members']:
            self.assertEqual(member['invite_status'], 'sms_sent')
            user_id = member['id']
            user = get_user_model().objects.get(id=user_id)

            phone_number = PhoneNumber.objects.create(
                phone_number="+1212{0}".format(user.id).ljust(12, '0'),
                user=user,
                date_created=timezone.now(),
                verified=True
            )

        album_before_response = self.client.get(album_url)
        j2 = json.loads(album_before_response.content)
        for member in j2['members']:
            self.assertEqual(member['invite_status'], 'joined')

        # TEST invitation_viewed status

        # This user not in Album #9
        album_user_ids = [usr['id'] for usr in j2['members']]
        inviter = User.objects.get(pk=album_user_ids[0])
        barney = User.objects.get(pk=3)
        self.assertNotIn(barney.id, album_user_ids)
        self.assertEqual(barney.phonenumber_set.count(), 0)

        phone_number = PhoneNumber.objects.create(
                phone_number = "+12127184123",
                user = barney,
                date_created = timezone.now(),
                verified = False)

        PhoneNumberLinkCode.objects.invite_phone_number(
                inviter,
                phone_number.phone_number,
                phone_number.user.nickname,
                timezone.now(),
                Album.default_sms_message_formatter,
                'Test',
                {})

        # Add barney to the album
        add_members = {'add_members': [
            {'user_id': barney.id}
        ]}
        add_response = self.client.post(album_url,
                                        content_type='application/json',
                                        data=json.dumps(add_members))


        j3 = json.loads(self.client.get(album_url).content)
        barney_status = [m['invite_status'] for m in j3['members'] if m['id'] == barney.id][0]
        self.assertEqual(barney_status, User.STATUS_SMS_SENT)

        # View invite
        with self.settings(ROOT_URLCONF='shotvibe_site.urls'):
            response = self.client.get(PhoneNumberLinkCode.objects.get(phone_number=phone_number).get_invite_page())
            self.assertEqual(response.status_code, httplib.OK)

        # Verify status
        j3 = json.loads(self.client.get(album_url).content)
        barney_status = [m['invite_status'] for m in j3['members'] if m['id'] == barney.id][0]
        self.assertEqual(barney_status, User.STATUS_INVITATION_VIEWED)

    def test_add_members(self):
        album_details_url = reverse('album-detail', kwargs={'pk': 9})
        album_before_response = self.client.get(album_details_url)
        members_before = json.loads(album_before_response.content)['members']
        etag = album_before_response['etag']

        add_members = { 'add_members': [
            { 'user_id': 3 },
            { 'user_id': 4 },
            { 'user_id': 12 }
            ] }

        add_response = self.client.post(album_details_url, content_type='application/json', data=json.dumps(add_members))
        self.assertEqual(add_response.status_code, 200)

        album_after_response = self.client.get(album_details_url, HTTP_IF_NONE_MATCH=etag)
        self.assertEqual(album_after_response.status_code, 200)

        members_after = json.loads(album_after_response.content)['members']

        members_ids_before = [u['id'] for u in members_before]
        members_ids_after = [u['id'] for u in members_after]
        self.assertEqual(set(members_ids_before + [3, 4, 12]), set(members_ids_after))


        # Add using separate endpoint
        users_not_in_album = User.objects.exclude(id__in=members_ids_after)[:3]
        data = {'members': []}
        for user in users_not_in_album:
            data['members'].append({'user_id': user.id})
        album_members_url = reverse('album-members', kwargs={'pk': 9})
        response = self.client.post(album_members_url,
                                    data=json.dumps(data),
                                    content_type='application/json')
        self.assertEqual(response.status_code, httplib.OK)
        response_array = json.loads(response.content)
        for item in response_array:
            self.assertTrue("success" in item)
            self.assertEqual(item.get('success'), True)

        # Verify that users were added
        album_after_response = self.client.get(album_details_url,
                                               HTTP_IF_NONE_MATCH=etag)
        members_after = json.loads(album_after_response.content)['members']
        u1 = [user.id for user in users_not_in_album]
        u2 = [user['id'] for user in members_after]
        self.assertTrue(all([_u1 in u2 for _u1 in u1]))

        # Add member with invalid ID
        data = {
            'members': [
                {
                    'user_id': 23498273984
                },
                {
                    'phone_number': '123',
                    'default_country': 'US',
                    'contact_nickname': 'John Doe'
                },
                {
                    'phone_number': 'abc',
                    'default_country': 'US',
                    'contact_nickname': 'John Doe'
                }
            ]
        }
        response = self.client.post(album_members_url,
                                    data=json.dumps(data),
                                    content_type='application/json')
        self.assertEqual(response.status_code, httplib.OK)
        response_array = json.loads(response.content)
        for item in response_array:
            self.assertTrue("success" in item)
            self.assertTrue("error" in item)
            self.assertEqual(item.get('success'), False)

        self.assertEqual(response_array[0].get('error'), 'invalid_user_id')
        self.assertEqual(response_array[1].get('error'), 'invalid_phone_number')
        self.assertEqual(response_array[2].get('error'), 'invalid_phone_number')

    def test_add_new_phone(self):
        album_before_response = self.client.get('/albums/9/')
        members_before = json.loads(album_before_response.content)['members']
        etag = album_before_response['etag']

        add_members = { 'add_members': [
            {
                'phone_number': '212-718-4000',
                'default_country': 'US',
                'contact_nickname': 'John Doe' }
            ] }

        add_response = self.client.post('/albums/9/', content_type='application/json', data=json.dumps(add_members))
        self.assertEqual(add_response.status_code, 200)

        album_after_response = self.client.get('/albums/9/', HTTP_IF_NONE_MATCH=etag)
        self.assertEqual(album_after_response.status_code, 200)

        members_after = json.loads(album_after_response.content)['members']

        members_ids_before = [u['id'] for u in members_before]
        members_ids_after = [u['id'] for u in members_after]

        added = set(members_ids_after) - set(members_ids_before)

        self.assertEqual(len(added), 1)

        user = auth.get_user_model().objects.get(pk=added.pop())
        user_phone = user.phonenumber_set.all()[0]

        self.assertEqual(user_phone.phone_number, '+12127184000')
        self.assertEqual(user_phone.verified, False)

        # Check that nicknames was assigned to the new users.
        nicknames_before = [u['nickname'] for u in members_before]
        nicknames_after = [u['nickname'] for u in members_after]

        new_nicknames = set(nicknames_after) - set(nicknames_before)
        expected_nicknames = [member_data['contact_nickname'] for member_data in add_members['add_members']]
        self.assertEqual(list(new_nicknames), expected_nicknames)

    def test_add_existing_phone(self):
        barney = auth.get_user_model().objects.get(pk=3)
        barney_nickname = barney.nickname
        barney_phone = PhoneNumber.objects.create(
                phone_number='+12127184000',
                user=barney,
                date_created=timezone.now(),
                verified=True)

        album_before_response = self.client.get('/albums/9/')
        members_before = json.loads(album_before_response.content)['members']
        etag = album_before_response['etag']

        add_members = { 'add_members': [
            {
                'phone_number': '212-718-4000',
                'default_country': 'US',
                'contact_nickname': 'this should not apply'
            }
        ]}

        add_response = self.client.post('/albums/9/', content_type='application/json', data=json.dumps(add_members))
        self.assertEqual(add_response.status_code, 200)

        album_after_response = self.client.get('/albums/9/', HTTP_IF_NONE_MATCH=etag)
        self.assertEqual(album_after_response.status_code, 200)

        members_after = json.loads(album_after_response.content)['members']

        members_ids_before = [u['id'] for u in members_before]
        members_ids_after = [u['id'] for u in members_after]

        self.assertEqual(set(members_ids_before + [3]), set(members_ids_after))

        nicknames_before = [u['nickname'] for u in members_before]
        nicknames_after = [u['nickname'] for u in members_after]

        self.assertEqual(set(nicknames_before + [barney_nickname]), set(nicknames_after))
        for member_data in add_members['add_members']:
            self.assertFalse(member_data['contact_nickname'] in nicknames_after)

    def test_add_dangling_phone(self):
        number = {
            'phone_number': '212-718-4000',
            'default_country': 'US',
            'contact_nickname': 'John Doe'
        }
        r = self.client.post('/auth/authorize_phone_number/', content_type='application/json', data=json.dumps(number))
        self.assertEqual(r.status_code, 200)

        self.assertEqual(PhoneNumber.objects.get(phone_number='+12127184000').verified, False)

        album_before_response = self.client.get('/albums/9/')
        members_before = json.loads(album_before_response.content)['members']
        etag = album_before_response['etag']

        add_members = { 'add_members': [
            {
                'phone_number': '212-718-4000',
                'default_country': 'US',
                'contact_nickname': 'hello world'
            }
        ]}

        add_response = self.client.post('/albums/9/', content_type='application/json', data=json.dumps(add_members))
        self.assertEqual(add_response.status_code, 200)

        self.assertEqual(PhoneNumber.objects.get(phone_number='+12127184000').verified, False)

        album_after_response = self.client.get('/albums/9/', HTTP_IF_NONE_MATCH=etag)
        self.assertEqual(album_after_response.status_code, 200)

        members_after = json.loads(album_after_response.content)['members']

        members_ids_before = [u['id'] for u in members_before]
        members_ids_after = [u['id'] for u in members_after]

        added = set(members_ids_after) - set(members_ids_before)

        self.assertEqual(len(added), 1)

        user = auth.get_user_model().objects.get(pk=added.pop())
        user_phone = user.phonenumber_set.all()[0]

        self.assertEqual(user_phone.phone_number, '+12127184000')
        self.assertEqual(user_phone.verified, False)

    def test_leave_album(self):
        # Currently logged in user is amanda, she will be removed from the album

        amanda = auth.get_user_model().objects.get(nickname="amanda")

        # Make sure amanda is in album members
        album_before_response = self.client.get(reverse('album-detail', kwargs={'pk':9}))
        members_before = json.loads(album_before_response.content)['members']
        self.assertTrue(amanda.nickname in [m['nickname'] for m in members_before])

        # Send leave album request
        leave_album_response = self.client.post(reverse('album-leave', kwargs={'pk':9}))
        # Response should be 204 No Content
        self.assertEqual(leave_album_response.status_code, httplib.NO_CONTENT)

        # Make sure amanda is not a member of the album anymore
        self.assertRaises(AlbumMember.DoesNotExist, AlbumMember.objects.filter(user=amanda, album__pk=9).get)

        # Retrieving album details is forbidden, because user is not a member of the album anymore
        album_after_response = self.client.get(reverse('album-detail', kwargs={'pk':9}))
        self.assertEqual(album_after_response.status_code, httplib.FORBIDDEN)


@mark_sms_test_case
class ScheduledSMSTest(BaseTestCase):
    class MockUrlConf(object):
        urlpatterns = patterns('',
                url(r'^', include(photos_api.urls)),
                url(r'^frontend/', include(frontend.urls)),
                )

    urls = MockUrlConf

    def setUp(self):
        try:
            d = SMSInviteMessage.objects.get(
                    country_calling_code = SMSInviteMessage.COUNTRY_DEFAULT_VALUE,
                    time_delay_hours = 0)
            d.message_template = 'Hi ${name}. ${inviter} shared an album: ${album}'
            d.save(update_fields=['message_template'])
        except:
            d = SMSInviteMessage.objects.create(
                    country_calling_code = SMSInviteMessage.COUNTRY_DEFAULT_VALUE,
                    time_delay_hours = 0,
                    message_template = 'Hi ${name}. ${inviter} shared an album: ${album}')

        SMSInviteMessage.objects.create(
                country_calling_code = SMSInviteMessage.COUNTRY_DEFAULT_VALUE,
                message_template = 'Hi ${name}. ${inviter} has been waiting 4 hours for you to view: ${album}',
                time_delay_hours = 4)

        SMSInviteMessage.objects.create(
                country_calling_code = SMSInviteMessage.COUNTRY_DEFAULT_VALUE,
                message_template = 'An entire day has passed',
                time_delay_hours = 24)

        self.client.login(username='2', password='amanda')

        # Create a phone number for amanda, to verify that the SMS's are sent
        # from her
        PhoneNumber.objects.create(
                phone_number = '+12127182002',
                user = get_user_model().objects.get(pk=2),
                date_created = datetime.datetime(1999, 01, 01, tzinfo=timezone.utc),
                verified = True)

    def test_send_all_invites(self):
        add_members = { 'members': [
            {
                'phone_number': '212-718-4000',
                'default_country': 'US',
                'contact_nickname': 'John Doe' }
            ] }

        now = timezone.now()
        add_response = self.client.post('/albums/9/members/', content_type='application/json', data=json.dumps(add_members))
        self.assertEqual(add_response.status_code, 200)

        phone_number = PhoneNumber.objects.get(phone_number='+12127184000')
        link_code = PhoneNumberLinkCode.objects.get(phone_number=phone_number)

        invite_url_prefix = 'https://i.useglance.com'
        link = link_code.get_invite_page(invite_url_prefix)

        self.assertEqual(send_sms.testing_outbox, [('+12127184000', 'Hi John Doe. amanda shared an album: cautioned whoa\n' + link, '+12127182002')])
        send_sms.testing_outbox = []

        # Start traveling into the future, and verify that the SMS's are sent
        # on time (after 4 hours, and after 24 hours):

        invites_manager.process_scheduled_invites(now + datetime.timedelta(hours=0.5))
        self.assertEqual(send_sms.testing_outbox, [])

        invites_manager.process_scheduled_invites(now + datetime.timedelta(hours=1.5))
        self.assertEqual(send_sms.testing_outbox, [])

        invites_manager.process_scheduled_invites(now + datetime.timedelta(hours=2.5))
        self.assertEqual(send_sms.testing_outbox, [])

        invites_manager.process_scheduled_invites(now + datetime.timedelta(hours=3.5))
        self.assertEqual(send_sms.testing_outbox, [])

        invites_manager.process_scheduled_invites(now + datetime.timedelta(hours=4.5))
        self.assertEqual(send_sms.testing_outbox, [('+12127184000', 'Hi John Doe. amanda has been waiting 4 hours for you to view: cautioned whoa\n' + link, '+12127182002')])
        send_sms.testing_outbox = []

        invites_manager.process_scheduled_invites(now + datetime.timedelta(hours=5.5))
        self.assertEqual(send_sms.testing_outbox, [])

        invites_manager.process_scheduled_invites(now + datetime.timedelta(hours=23.5))
        self.assertEqual(send_sms.testing_outbox, [])

        invites_manager.process_scheduled_invites(now + datetime.timedelta(hours=24.5))
        self.assertEqual(send_sms.testing_outbox, [('+12127184000', u'An entire day has passed\n' + link, '+12127182002')])

    def test_clear_invites_after_link_visit(self):
        add_members = { 'members': [
            {
                'phone_number': '212-718-4000',
                'default_country': 'US',
                'contact_nickname': 'John Doe' }
            ] }

        now = timezone.now()
        add_response = self.client.post('/albums/9/members/', content_type='application/json', data=json.dumps(add_members))
        self.assertEqual(add_response.status_code, 200)

        phone_number = PhoneNumber.objects.get(phone_number='+12127184000')
        link_code = PhoneNumberLinkCode.objects.get(phone_number=phone_number)

        invite_url_prefix = 'https://i.useglance.com'
        link = link_code.get_invite_page(invite_url_prefix)

        self.assertEqual(send_sms.testing_outbox, [('+12127184000', 'Hi John Doe. amanda shared an album: cautioned whoa\n' + link, '+12127182002')])
        send_sms.testing_outbox = []

        # Start traveling into the future, and verify that the SMS's are sent
        # on time (after 4 hours, and after 24 hours):

        invites_manager.process_scheduled_invites(now + datetime.timedelta(hours=0.5))
        self.assertEqual(send_sms.testing_outbox, [])

        invites_manager.process_scheduled_invites(now + datetime.timedelta(hours=1.5))
        self.assertEqual(send_sms.testing_outbox, [])

        invites_manager.process_scheduled_invites(now + datetime.timedelta(hours=2.5))
        self.assertEqual(send_sms.testing_outbox, [])

        invites_manager.process_scheduled_invites(now + datetime.timedelta(hours=3.5))
        self.assertEqual(send_sms.testing_outbox, [])

        invites_manager.process_scheduled_invites(now + datetime.timedelta(hours=4.5))
        self.assertEqual(send_sms.testing_outbox, [('+12127184000', 'Hi John Doe. amanda has been waiting 4 hours for you to view: cautioned whoa\n' + link, '+12127182002')])
        send_sms.testing_outbox = []

        invites_manager.process_scheduled_invites(now + datetime.timedelta(hours=5.5))
        self.assertEqual(send_sms.testing_outbox, [])

        # Now have 'John Doe' visit the invite link:
        sterile_client = Client()
        invite_response = sterile_client.get(reverse('invite_page', kwargs={'invite_code':link_code.invite_code}))
        self.assertEqual(invite_response.status_code, 200)


        # After visiting the invite link, no more SMS invites should be sent:

        invites_manager.process_scheduled_invites(now + datetime.timedelta(hours=23.5))
        self.assertEqual(send_sms.testing_outbox, [])

        invites_manager.process_scheduled_invites(now + datetime.timedelta(hours=24.5))
        self.assertEqual(send_sms.testing_outbox, [])


class TestPhoneNumberMobile(TestCase):
    def test_1(self):
        # "97254", "97252", "97250", "97258" These are prefixes for mobile
        # numbers in Israel
        self.assertTrue(is_phone_number_mobile(phonenumbers.parse("+972541231212")))
        self.assertTrue(is_phone_number_mobile(phonenumbers.parse("+972521231212")))
        self.assertTrue(is_phone_number_mobile(phonenumbers.parse("+972501231212")))
        self.assertTrue(is_phone_number_mobile(phonenumbers.parse("+972581231212")))
        self.assertFalse(is_phone_number_mobile(phonenumbers.parse("+97231231212")))
        self.assertTrue(is_phone_number_mobile(phonenumbers.parse("+12127184000")))


@override_settings(PRIVATE_API_KEY="the-secret-api-key")
class PrivateApiTestCase(BaseTestCase):
    def test_no_authorization_header(self):
        result = self.client.post(reverse('photo-upload-init', kwargs={'photo_id':'dummy-photo-id'}))
        self.assertEqual(result.status_code, 401)

    def test_wrong_authorization_header(self):
        result = self.client.post(reverse('photo-upload-init', kwargs={'photo_id':'dummy-photo-id'}),
                HTTP_AUTHORIZATION='Key wrong-secret')
        self.assertEqual(result.status_code, 401)

    def test_correct_authentication(self):
        result = self.client.post(reverse('photo-upload-init', kwargs={'photo_id':'dummy-photo-id'}),
                HTTP_AUTHORIZATION='Key ' + settings.PRIVATE_API_KEY)
        self.assertNotEqual(result.status_code, 401)

    def test_photo_upload_init_bad_request(self):
        bad_data = { 'foo': 'bar' }
        result = self.client.post(reverse('photo-upload-init', kwargs={'photo_id':'dummy-photo-id'}),
                HTTP_AUTHORIZATION='Key ' + settings.PRIVATE_API_KEY,
                data=json.dumps(bad_data),
                content_type="application/json")
        self.assertEqual(result.status_code, 400)

    def test_photo_upload_init_user_auth_failed(self):
        body = { 'user_auth_token': 'invalid-token' }
        response = self.client.post(reverse('photo-upload-init', kwargs={'photo_id':'dummy-photo-id'}),
                HTTP_AUTHORIZATION='Key ' + settings.PRIVATE_API_KEY,
                data=json.dumps(body),
                content_type="application/json")
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['success'], False)
        self.assertEqual(response_data['error'], 'user_auth_failed')

    def test_photo_upload_init_invalid_photo_id(self):
        amanda = User.objects.get(nickname='amanda')
        user_auth_token = AuthToken.objects.create_auth_token(amanda, 'Test Token', timezone.now())
        body = { 'user_auth_token': user_auth_token.key }
        response = self.client.post(reverse('photo-upload-init', kwargs={'photo_id':'invalid-photo-id'}),
                HTTP_AUTHORIZATION='Key ' + settings.PRIVATE_API_KEY,
                data=json.dumps(body),
                content_type="application/json")

        self.assertEqual(response.status_code, 404)

    def test_photo_upload_init_ok(self):
        amanda = User.objects.get(nickname='amanda')
        user_auth_token = AuthToken.objects.create_auth_token(amanda, 'Test Token', timezone.now())
        pending_photo = Photo.objects.upload_request(amanda)
        body = { 'user_auth_token': user_auth_token.key }
        response = self.client.post(reverse('photo-upload-init', kwargs={'photo_id':pending_photo.photo_id}),
                HTTP_AUTHORIZATION='Key ' + settings.PRIVATE_API_KEY,
                data=json.dumps(body),
                content_type="application/json")

        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['success'], True)
        self.assertEqual(response_data['storage_id'], pending_photo.storage_id)

    def test_photo_upload_complete_ok(self):
        amanda = User.objects.get(nickname='amanda')
        pending_photo = Photo.objects.upload_request(amanda)
        self.assertFalse(pending_photo.is_file_uploaded())
        response = self.client.put(reverse('photo-file-uploaded', kwargs={'photo_id':pending_photo.photo_id}),
                HTTP_AUTHORIZATION='Key ' + settings.PRIVATE_API_KEY)
        self.assertEqual(response.status_code, 204)
        # Refresh pending_photo to get latest data from DB
        pending_photo = PendingPhoto.objects.get(photo_id=pending_photo.photo_id)
        self.assertTrue(pending_photo.is_file_uploaded())

    def test_photo_upload_processing_done_ok(self):
        amanda = User.objects.get(nickname='amanda')
        pending_photo = Photo.objects.upload_request(amanda)
        self.assertFalse(pending_photo.is_processing_done())
        response = self.client.put(reverse('photo-file-uploaded', kwargs={'photo_id':pending_photo.photo_id}),
                HTTP_AUTHORIZATION='Key ' + settings.PRIVATE_API_KEY)
        self.assertEqual(response.status_code, 204)
        response = self.client.put(reverse('photo-processing-done', kwargs={'storage_id':pending_photo.storage_id}),
                HTTP_AUTHORIZATION='Key ' + settings.PRIVATE_API_KEY)
        self.assertEqual(response.status_code, 204)
        # Refresh pending_photo to get latest data from DB
        pending_photo = PendingPhoto.objects.get(photo_id=pending_photo.photo_id)
        self.assertTrue(pending_photo.is_processing_done())
