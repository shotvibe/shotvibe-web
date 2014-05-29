import datetime

from django.utils.timezone import utc
from django.test import TestCase

from phone_auth.models import User, PhoneNumber
from photos.models import Album, AlbumMember

from invites_manager.models import SMSInviteProcessor, SMSInviteMessage


class PretendSMSSender(object):
    def __init__(self):
        self.clear_sentbox()

    def __call__(self, destination_phone, message, sender_phone=None):
        self.sentbox.append((destination_phone, message, sender_phone))

    def clear_sentbox(self):
        self.sentbox = []


class InviteTest(TestCase):
    def setUp(self):
        self.pretend_sms_sender = PretendSMSSender()
        self.sms_invite_processor = SMSInviteProcessor(self.pretend_sms_sender)

        self.amanda = User.objects.create_user('amanda')
        PhoneNumber.objects.create(
                phone_number = '+12127182002',
                user = self.amanda,
                date_created = datetime.datetime(1999, 01, 01, tzinfo=utc),
                verified = True)

        self.party_album = Album.objects.create_album(self.amanda, 'Party', datetime.datetime(2000, 01, 01, tzinfo=utc))

    def test_single_default_invite(self):
        SMSInviteMessage.objects.create(
                country_calling_code = None, # Use as default
                message_template = 'Hi ${name}. ${inviter} shared an album: ${album}',
                time_delay_hours = 0)

        the_time = datetime.datetime(2000, 01, 02, tzinfo=utc)

        new_user = User.objects.create_user(nickname='barney')
        phone_number = PhoneNumber.objects.create(
                phone_number = '+12127182003',
                user = new_user,
                date_created = the_time,
                verified = False)

        AlbumMember.objects.create(
                user = new_user,
                album = self.party_album,
                added_by_user = self.amanda,
                datetime_added = the_time)

        link_code = self.sms_invite_processor.send_invite(self.amanda, phone_number, the_time)

        invite_url_prefix = 'https://useglance.com'
        link = link_code.get_invite_page(invite_url_prefix)

        self.assertEqual(self.pretend_sms_sender.sentbox, [('+12127182003', u'Hi barney. amanda shared an album: Party\n' + link, '+12127182002')])

    def test_scheduled_default_invites(self):
        SMSInviteMessage.objects.create(
                country_calling_code = None, # Use as default
                message_template = 'Hi ${name}. ${inviter} shared an album: ${album}',
                time_delay_hours = 0)

        SMSInviteMessage.objects.create(
                country_calling_code = None, # Use as default
                message_template = 'Hi ${name}. ${inviter} has been waiting 2 hours for you to view: ${album}',
                time_delay_hours = 2)

        SMSInviteMessage.objects.create(
                country_calling_code = None, # Use as default
                message_template = 'An entire day has passed',
                time_delay_hours = 24)

        the_time = datetime.datetime(2000, 01, 02, tzinfo=utc)

        new_user = User.objects.create_user(nickname='barney')
        phone_number = PhoneNumber.objects.create(
                phone_number = '+12127182003',
                user = new_user,
                date_created = the_time,
                verified = False)

        AlbumMember.objects.create(
                user = new_user,
                album = self.party_album,
                added_by_user = self.amanda,
                datetime_added = the_time)

        link_code = self.sms_invite_processor.send_invite(self.amanda, phone_number, the_time)

        invite_url_prefix = 'https://useglance.com'
        link = link_code.get_invite_page(invite_url_prefix)

        self.assertEqual(self.pretend_sms_sender.sentbox, [('+12127182003', u'Hi barney. amanda shared an album: Party\n' + link, '+12127182002')])
        self.pretend_sms_sender.clear_sentbox()

        self.sms_invite_processor.process_scheduled_invites(datetime.datetime(2000, 01, 02, 0, 0, 0, tzinfo=utc))
        self.assertEqual(self.pretend_sms_sender.sentbox, [])

        self.sms_invite_processor.process_scheduled_invites(datetime.datetime(2000, 01, 02, 1, 0, 0, tzinfo=utc))
        self.assertEqual(self.pretend_sms_sender.sentbox, [])

        self.sms_invite_processor.process_scheduled_invites(datetime.datetime(2000, 01, 02, 2, 0, 0, tzinfo=utc))
        self.assertEqual(self.pretend_sms_sender.sentbox, [(u'+12127182003', u'Hi barney. amanda has been waiting 2 hours for you to view: Party\n' + link, '+12127182002')])
        self.pretend_sms_sender.clear_sentbox()

        self.sms_invite_processor.process_scheduled_invites(datetime.datetime(2000, 01, 02, 3, 0, 0, tzinfo=utc))
        self.assertEqual(self.pretend_sms_sender.sentbox, [])
        self.pretend_sms_sender.clear_sentbox()

        self.sms_invite_processor.process_scheduled_invites(datetime.datetime(2000, 01, 02, 23, 0, 0, tzinfo=utc))
        self.assertEqual(self.pretend_sms_sender.sentbox, [])
        self.pretend_sms_sender.clear_sentbox()

        self.sms_invite_processor.process_scheduled_invites(datetime.datetime(2000, 01, 02, 23, 59, 0, tzinfo=utc))
        self.assertEqual(self.pretend_sms_sender.sentbox, [])
        self.pretend_sms_sender.clear_sentbox()

        self.sms_invite_processor.process_scheduled_invites(datetime.datetime(2000, 01, 03, 2, 0, 0, tzinfo=utc))
        self.assertEqual(self.pretend_sms_sender.sentbox, [(u'+12127182003', u'An entire day has passed\n' + link, u'+12127182002')])
        self.pretend_sms_sender.clear_sentbox()

        self.sms_invite_processor.process_scheduled_invites(datetime.datetime(2000, 01, 03, 2, 0, 1, tzinfo=utc))
        self.assertEqual(self.pretend_sms_sender.sentbox, [])
        self.pretend_sms_sender.clear_sentbox()
