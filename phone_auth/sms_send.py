import HTMLParser
import random

import phonenumbers
import requests

from twilio import TwilioException
from twilio.rest import TwilioRestClient

from django.conf import settings
from django.core import mail

COUNTRY_CODE_ISRAEL = 972

def is_test_number(phone):
    if not isinstance(phone, phonenumbers.PhoneNumber):
        phone = phonenumbers.parse(phone)

    if phone.country_code == 1:
        e164 = phonenumbers.format_number(phone, phonenumbers.PhoneNumberFormat.E164)

        # Numbers of the form +1-212-718-xxxx are not issued, and are used as
        # test numbers
        #
        # Reference:
        # http://en.wikipedia.org/wiki/North_American_Numbering_Plan#Fictional_telephone_numbers
        # http://en.wikipedia.org/wiki/Fictitious_telephone_number#North_American_Numbering_Plan
        if e164[0:8] == '+1212718':
            return True

    return False

def in_testing_mode():
    # An evil hack to detect if we are running unit tests
    # http://stackoverflow.com/questions/6957016/detect-django-testing-mode
    return hasattr(mail, 'outbox')

def send_sms(destination_phone, message, sender_phone=None):
    """
    destination_phone must be formatted as international E164

    sender_phone must be formatted as international E164, or it may be "None"
    Note that the system will make a "best effort" to make the SMS appear to be
    sent from sender_phone, but it may not succeed
    """
    p = phonenumbers.parse(destination_phone)

    # Don't actually send any SMS messages during unit tests
    if in_testing_mode():
        return

    # Don't actually send any SMS messages for test numbers
    if is_test_number(p):
        return

    default_sender = send_sms_twilio
    country_overrides = {
        COUNTRY_CODE_ISRAEL: send_sms_smartsms
        }

    sender = country_overrides.get(p.country_code, default_sender)
    sender(p, message, sender_phone)

    # TODO Log that the SMS was sent

def send_sms_twilio(phone, message, sender_phone=None):
    """
    Twilio does not support setting a source number, so the "sender_phone"
    argument is ignored
    """
    if not isinstance(phone, phonenumbers.phonenumber.PhoneNumber):
        raise ValueError('phone must be a PhoneNumber object')

    account = settings.TWILIO_CREDENTIALS['account']
    token = settings.TWILIO_CREDENTIALS['auth_token']
    from_phone_numbers = settings.TWILIO_CREDENTIALS['phone_numbers']

    # Sending is done from a random number
    chosen_from_phone_number = random.choice(from_phone_numbers)

    phone_e164 = phonenumbers.format_number(phone, phonenumbers.PhoneNumberFormat.E164)

    def log_error(message):
        # TODO Better logging ...
        print message

    client = TwilioRestClient(account, token)
    try:
        client.messages.create(
                to=phone_e164,
                from_=chosen_from_phone_number,
                body=message)
    except TwilioException as e:
        log_error(unicode(e))
        return

# Used to send SMS to phone numbers in Israel
# http://www.smartsms.co.il
def send_sms_smartsms(phone, message, sender_phone=None):
    if not isinstance(phone, phonenumbers.phonenumber.PhoneNumber):
        raise ValueError('phone must be a PhoneNumber object')

    if phone.country_code != COUNTRY_CODE_ISRAEL:
        raise Exception('SmartSMS can only send SMS messages to phone numbers in Israel. Tried to send to number: ' + str(phone))

    phone_e164 = phonenumbers.format_number(phone, phonenumbers.PhoneNumberFormat.E164)

    # Strip the leading plus:
    phone_final = phone_e164[1:]

    smartsms_url = 'http://smartsms.co.il/member/http_sms_api.php'

    if sender_phone:
        # Strip the leading plus:
        source_phone_number = sender_phone[1:]
    else:
        # This can be any phone number:
        source_phone_number = '1555'

    username = settings.SMARTSMS_CREDENTIALS['username']
    password = settings.SMARTSMS_CREDENTIALS['password']

    payload = {
            'UN': username,
            'P': password,
            'DA': phone_final,
            'SA': source_phone_number,
            'M': message
            }

    def log_error(message):
        # TODO Better logging ...
        print message.encode('utf8')

    try:
        r = requests.post(smartsms_url, data=payload)
        r.raise_for_status()
    except requests.exceptions.RequestException as e:
        log_error(unicode(e))
        return

    # SmartSMS has an ugly API:
    # It returns an HTTP status code of 200 even on error. And it returns a pseudo-XML response that needs to HTML entity decoded
    class ResponseHTMLParser(HTMLParser.HTMLParser):
        def __init__(self):
            HTMLParser.HTMLParser.__init__(self)
            self.state = 'waiting_for_root'
        def handle_starttag(self, tag, attrs):
            if tag == 'br':
                return

            if self.state == 'waiting_for_root':
                if tag == 'error':
                    self.state = 'error'
                elif tag == 'success':
                    self.state = 'success'
        def handle_endtag(self, tag):
            pass
        def handle_data(self, data):
            pass
    h = ResponseHTMLParser()
    response_xml = h.unescape(r.text)
    h.feed(response_xml)
    if h.state != 'success':
        log_error('Error Response: ' + response_xml)
