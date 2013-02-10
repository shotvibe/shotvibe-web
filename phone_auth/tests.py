import datetime
import json

from django.contrib import auth
from django.test import TestCase
from django.utils.timezone import utc

from phone_auth.models import AuthToken, PhoneNumber, PhoneNumberConfirmSMSCode

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
