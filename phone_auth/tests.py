import datetime
import json
import urlparse

from django.contrib import auth
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.utils.timezone import utc

from phone_auth.models import AuthToken, User, PhoneNumber, PhoneNumberConfirmSMSCode, PhoneNumberLinkCode
from phone_auth.views import app_init
from photos.models import Album, AlbumMember
from frontend.mobile_views import invite_page

class ModelTests(TestCase):
    fixtures = ['tests/test_users']

    def test_create_auth_token(self):
        amanda = auth.get_user_model().objects.get(pk=2)
        the_date = datetime.datetime(2010, 1, 1, tzinfo=utc)
        token = AuthToken.objects.create_auth_token(amanda, 'iPhone 3GS', the_date)
        self.assertEqual(token.user, amanda)
        self.assertEqual(token.description, 'iPhone 3GS')
        self.assertEqual(token.date_created, the_date)
        self.assertEqual(token.last_access, the_date)

    def test_authorize_phone_number_new(self):
        before_users = auth.get_user_model().objects.all().count()
        confirmation_key = PhoneNumber.objects.authorize_phone_number('+12127184000')
        after_users = auth.get_user_model().objects.all().count()

        # A new user should have been created
        self.assertEqual(after_users, before_users + 1)

        phone_number = PhoneNumber.objects.get(phone_number='+12127184000')
        self.assertEqual(phone_number.verified, False)

        confirm = PhoneNumberConfirmSMSCode.objects.get(confirmation_key=confirmation_key)
        self.assertEqual(confirm.phone_number, phone_number)

    def test_authorize_phone_number_existing(self):
        PhoneNumber.objects.authorize_phone_number('+12127184000')
        existing_user = PhoneNumber.objects.get(phone_number='+12127184000').user

        before_users = auth.get_user_model().objects.all().count()
        confirmation_key = PhoneNumber.objects.authorize_phone_number('+12127184000')
        after_users = auth.get_user_model().objects.all().count()

        # No new users should have been created
        self.assertEqual(after_users, before_users)

        phone_number = PhoneNumber.objects.get(phone_number='+12127184000')
        self.assertEqual(phone_number.user, existing_user)

        confirm = PhoneNumberConfirmSMSCode.objects.get(confirmation_key=confirmation_key)
        self.assertEqual(confirm.phone_number, phone_number)

    def test_confirm_phone_number_expired(self):
        result = PhoneNumber.objects.confirm_phone_number('nonexisting_dummy_confirmation_key', '6666', 'iPhone 3GS')
        self.assertFalse(result.success)
        self.assertTrue(result.expired_key)
        self.assertFalse(result.incorrect_code)

    def test_confirm_phone_number_incorrect_code(self):
        confirmation_key = PhoneNumber.objects.authorize_phone_number('+12127184000')
        result = PhoneNumber.objects.confirm_phone_number(confirmation_key, 'wrong-code', 'iPhone 3GS')
        self.assertFalse(result.success)
        self.assertFalse(result.expired_key)
        self.assertTrue(result.incorrect_code)

    def test_confirm_phone_number_valid(self):
        confirmation_key = PhoneNumber.objects.authorize_phone_number('+12127184000')
        confirmation_code = '6666' # Default code currently used for testing
        result = PhoneNumber.objects.confirm_phone_number(confirmation_key, confirmation_code, 'iPhone 3GS')
        self.assertTrue(result.success)

        user = result.user
        auth_token = result.auth_token

        token = AuthToken.objects.get(key=auth_token)
        self.assertEqual(token.user, user)
        self.assertEqual(token.description, 'iPhone 3GS')

class ViewTests(TestCase):
    fixtures = ['tests/test_users']
    urls = 'phone_auth.urls'

    def test_authorize_phone_number(self):
        number = {
                'phone_number': '212-718-4000',
                'default_country': 'US'
                }
        response = self.client.post('/authorize_phone_number/', content_type='application/json', data=json.dumps(number))
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(json.loads(response.content)['confirmation_key'], basestring)

    def test_authorize_invalid_phone_number(self):
        number = {
                'phone_number': '2',
                'default_country': 'US'
                }
        response = self.client.post('/authorize_phone_number/', content_type='application/json', data=json.dumps(number))
        self.assertEqual(response.status_code, 400)

    def test_authorize_invalid_country(self):
        number = {
                'phone_number': '212-718-4000-9999',
                'default_country': 'US'
                }
        response = self.client.post('/authorize_phone_number/', content_type='application/json', data=json.dumps(number))
        self.assertEqual(response.status_code, 400)

    def test_authorize_invalid_data(self):
        number = {
                'phone_number': '212-718-4000'
                }
        response = self.client.post('/authorize_phone_number/', content_type='application/json', data=json.dumps(number))
        self.assertEqual(response.status_code, 400)

    def test_confirm_sms_code(self):
        number = {
                'phone_number': '212-718-4000',
                'default_country': 'US'
                }
        auth_response = self.client.post('/authorize_phone_number/', content_type='application/json', data=json.dumps(number))
        confirmation_key = json.loads(auth_response.content)['confirmation_key']

        confirm = {
                'confirmation_code': '6666', # Default code currently used for testing
                'device_description': 'iPhone 3GS'
                }
        confirm_response = self.client.post('/confirm_sms_code/{0}/'.format(confirmation_key), content_type='application/json', data=json.dumps(confirm))
        self.assertEqual(confirm_response.status_code, 200)
        self.assertIsInstance(json.loads(confirm_response.content)['auth_token'], basestring)
        self.assertIn('user_id', json.loads(confirm_response.content))

    def test_confirm_sms_code_expired(self):
        confirm = {
                'confirmation_code': '6666', # Default code currently used for testing
                'device_description': 'iPhone 3GS'
                }
        confirm_response = self.client.post('/confirm_sms_code/{0}/'.format('nonexisting_dummy_confirmation_key'), content_type='application/json', data=json.dumps(confirm))
        self.assertEqual(confirm_response.status_code, 410)

    def test_confirm_sms_incorrect_code(self):
        number = {
                'phone_number': '212-718-4000',
                'default_country': 'US'
                }
        auth_response = self.client.post('/authorize_phone_number/', content_type='application/json', data=json.dumps(number))
        confirmation_key = json.loads(auth_response.content)['confirmation_key']

        confirm = {
                'confirmation_code': 'wrong-code',
                'device_description': 'iPhone 3GS'
                }
        confirm_response = self.client.post('/confirm_sms_code/{0}/'.format(confirmation_key), content_type='application/json', data=json.dumps(confirm))
        self.assertEqual(confirm_response.status_code, 403)

    def test_phone_number_verified(self):
        number = {
                'phone_number': '212-718-4000',
                'default_country': 'US'
                }
        auth_response = self.client.post('/authorize_phone_number/', content_type='application/json', data=json.dumps(number))
        confirmation_key = json.loads(auth_response.content)['confirmation_key']

        self.assertEqual(PhoneNumber.objects.get(phone_number='+12127184000').verified, False)

        confirm = {
                'confirmation_code': '6666', # Default code currently used for testing
                'device_description': 'iPhone 3GS'
                }
        self.client.post('/confirm_sms_code/{0}/'.format(confirmation_key), content_type='application/json', data=json.dumps(confirm))

        self.assertEqual(PhoneNumber.objects.get(phone_number='+12127184000').verified, True)

    def test_phone_number_not_verified(self):
        number = {
                'phone_number': '212-718-4000',
                'default_country': 'US'
                }
        auth_response = self.client.post('/authorize_phone_number/', content_type='application/json', data=json.dumps(number))
        confirmation_key = json.loads(auth_response.content)['confirmation_key']

        self.assertEqual(PhoneNumber.objects.get(phone_number='+12127184000').verified, False)

        confirm = {
                'confirmation_code': 'wrong-code',
                'device_description': 'iPhone 3GS'
                }
        self.client.post('/confirm_sms_code/{0}/'.format(confirmation_key), content_type='application/json', data=json.dumps(confirm))

        self.assertEqual(PhoneNumber.objects.get(phone_number='+12127184000').verified, False)

    def test_logout(self):
        number = {
                'phone_number': '212-718-4000',
                'default_country': 'US'
                }
        auth_response = self.client.post('/authorize_phone_number/', content_type='application/json', data=json.dumps(number))
        confirmation_key = json.loads(auth_response.content)['confirmation_key']

        confirm = {
                'confirmation_code': '6666', # Default code currently used for testing
                'device_description': 'iPhone 3GS'
                }
        confirm_response = self.client.post('/confirm_sms_code/{0}/'.format(confirmation_key), content_type='application/json', data=json.dumps(confirm))
        auth_token = json.loads(confirm_response.content)['auth_token']

        self.assertTrue(AuthToken.objects.filter(key=auth_token).exists())

        r = self.client.post('/logout/', content_type='application/json', HTTP_AUTHORIZATION='Token ' + auth_token)
        self.assertEqual(r.status_code, 200)

        self.assertFalse(AuthToken.objects.filter(key=auth_token).exists())

    def test_delete(self):
        self.assertTrue(auth.get_user_model().objects.filter(id=2).exists())

        self.client.login(username='2', password='amanda')

        r = self.client.post('/delete_account/')
        self.assertEqual(r.status_code, 200)

        self.assertFalse(auth.get_user_model().objects.filter(id=2).exists())


class InviteTests(TestCase):
    def setUp(self):
        self.tom = User.objects.create_user(nickname='tom')
        the_date = datetime.datetime(2010, 1, 1, tzinfo=utc)
        self.party_album = Album.objects.create_album(self.tom, 'Party', the_date)

    def test_album_invite_phone(self):
        later_on = datetime.datetime(2010, 1, 2, tzinfo=utc)
        self.party_album.add_members(self.tom, [], ['+12127184000'], later_on)

        self.assertEqual(AlbumMember.objects.filter(album=self.party_album).count(), 2)

        album_members_qs = AlbumMember.objects.filter(album=self.party_album).exclude(user=self.tom)
        self.assertTrue(album_members_qs.count()>0, "New user was not added to the AlbumMembers model")
        new_user = album_members_qs[0].user

        new_user_phone_numbers = new_user.phonenumber_set.all()
        self.assertEqual(len(new_user_phone_numbers), 1)

        new_user_phone_number = new_user_phone_numbers[0]
        self.assertEqual(new_user_phone_number.phone_number, '+12127184000')
        self.assertEqual(new_user_phone_number.date_created, later_on)
        self.assertEqual(new_user_phone_number.verified, False)

        link_code_object = PhoneNumberLinkCode.objects.get(phone_number=new_user_phone_number)
        self.assertEqual(link_code_object.inviting_user, self.tom)
        self.assertEqual(link_code_object.date_created, later_on)

    def test_mobile_invite_page(self):
        later_on = datetime.datetime(2010, 1, 2, tzinfo=utc)
        self.party_album.add_members(self.tom, [], ['+12127184000'], later_on)
        album_members_qs = AlbumMember.objects.filter(album=self.party_album).exclude(user=self.tom)
        self.assertTrue(album_members_qs.count()>0, "New user was not added to the AlbumMembers model")
        new_user = album_members_qs[0].user
        link_code_object = PhoneNumberLinkCode.objects.get(phone_number=new_user.phonenumber_set.all()[0])

        r = self.client.get(reverse(invite_page, args=(link_code_object.invite_code,)))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context['inviting_user'], self.tom)
        self.assertEqual(r.context['album'], self.party_album)

        self.assertEqual(self.client.session['phone_number'], '+12127184000')

    def test_app_init_no_session(self):
        r = self.client.get(reverse(app_init) + '?app=android&device_description=test')
        self.assertEqual(r.status_code, 302)
        url = urlparse.urlparse(r['Location'])
        query_str = url.query
        if not query_str:
            # Python's urlparse module sometimes will not parse the query
            # string for schemes that it doesn't like, so we have to extract it
            # manually
            query_str = url.path[url.path.find('?')+1:]
        self.assertEqual(url.scheme, 'shotvibe')
        query = urlparse.parse_qs(query_str, strict_parsing=True)
        self.assertEqual(len(query['country_code'][0]), 2)

        # Make sure that there is no 'user_id' and 'auth_token'
        self.assertNotIn('user_id', query)
        self.assertNotIn('auth_token', query)

    def test_app_init_with_session(self):
        later_on = datetime.datetime(2010, 1, 2, tzinfo=utc)
        self.party_album.add_members(self.tom, [], ['+12127184000'], later_on)
        album_members_qs = AlbumMember.objects.filter(album=self.party_album).exclude(user=self.tom)
        self.assertTrue(album_members_qs.count()>0, "New user was not added to the AlbumMembers model")
        new_user = album_members_qs[0].user
        link_code_object = PhoneNumberLinkCode.objects.get(phone_number=new_user.phonenumber_set.all()[0])

        # Visit the invite_page so that the session data is associated with the client
        self.client.get(reverse(invite_page, args=(link_code_object.invite_code,)))

        r = self.client.get(reverse(app_init) + '?app=android&device_description=test')
        self.assertEqual(r.status_code, 302)
        url = urlparse.urlparse(r['Location'])
        query_str = url.query
        if not query_str:
            # Python's urlparse module sometimes will not parse the query
            # string for schemes that it doesn't like, so we have to extract it
            # manually
            query_str = url.path[url.path.find('?')+1:]
        self.assertEqual(url.scheme, 'shotvibe')
        query = urlparse.parse_qs(query_str, strict_parsing=True)
        self.assertEqual(len(query['country_code'][0]), 2)
        self.assertEqual(int(query['user_id'][0]), new_user.id)
        auth_token = AuthToken.objects.get(key=query['auth_token'][0])
        self.assertEqual(auth_token.description, 'test')
        self.assertEqual(auth_token.user, new_user)

    def test_app_init_deletes_data(self):
        later_on = datetime.datetime(2010, 1, 2, tzinfo=utc)
        self.party_album.add_members(self.tom, [], ['+12127184000'], later_on)
        album_members_qs = AlbumMember.objects.filter(album=self.party_album).exclude(user=self.tom)
        self.assertTrue(album_members_qs.count()>0, "New user was not added to the AlbumMembers model")
        new_user = album_members_qs[0].user
        link_code_object = PhoneNumberLinkCode.objects.get(phone_number=new_user.phonenumber_set.all()[0])
        invite_code = link_code_object.invite_code

        # Visit the invite_page so that the session data is associated with the client
        self.client.get(reverse(invite_page, args=(invite_code,)))

        r = self.client.get(reverse(app_init) + '?app=android&device_description=test')
        self.assertEqual(r.status_code, 302)

        self.assertEqual(PhoneNumberLinkCode.objects.filter(invite_code=invite_code).count(), 0)
        self.assertNotIn('phone_number', self.client.session)

    def test_app_init_phone_verified(self):
        later_on = datetime.datetime(2010, 1, 2, tzinfo=utc)
        self.party_album.add_members(self.tom, [], ['+12127184000'], later_on)

        album_members_qs = AlbumMember.objects.filter(album=self.party_album).exclude(user=self.tom)
        self.assertTrue(album_members_qs.count()>0, "New user was not added to the AlbumMembers model")
        new_user = album_members_qs[0].user
        link_code_object = PhoneNumberLinkCode.objects.get(phone_number=new_user.phonenumber_set.all()[0])

        self.assertEqual(PhoneNumber.objects.get(phone_number='+12127184000').verified, False)

        # Visit the invite_page so that the session data is associated with the client
        self.client.get(reverse(invite_page, args=(link_code_object.invite_code,)))

        self.assertEqual(PhoneNumber.objects.get(phone_number='+12127184000').verified, False)

        r = self.client.get(reverse(app_init) + '?app=android&device_description=test')
        self.assertEqual(r.status_code, 302)

        self.assertEqual(PhoneNumber.objects.get(phone_number='+12127184000').verified, True)
