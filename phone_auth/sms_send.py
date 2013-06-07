import HTMLParser
import random

import phonenumbers
import requests

from twilio import TwilioException
from twilio.rest import TwilioRestClient

from django.conf import settings

COUNTRY_CODE_ISRAEL = 972

def is_test_number(phone):
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

def send_sms(destination_phone, message):
    """
    destination_phone must be formatted as international E164
    """
    p = phonenumbers.parse(destination_phone)

    # Don't actually send any SMS messages for test numbers
    if is_test_number(p):
        return

    default_sender = send_sms_twilio
    country_overrides = {
        COUNTRY_CODE_ISRAEL: send_sms_smartsms
        }

    sender = country_overrides.get(p.country_code, default_sender)
    sender(p, message)

    # TODO Log that the SMS was sent

def send_sms_twilio(phone, message):
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
        client.sms.messages.create(
                to=phone_e164,
                from_=chosen_from_phone_number,
                body=message)
    except TwilioException as e:
        log_error(unicode(e))
        return

# Used to send SMS to phone numbers in Israel
# http://www.smartsms.co.il
def send_sms_smartsms(phone, message):
    if not isinstance(phone, phonenumbers.phonenumber.PhoneNumber):
        raise ValueError('phone must be a PhoneNumber object')

    if phone.country_code != COUNTRY_CODE_ISRAEL:
        raise Exception('SmartSMS can only send SMS messages to phone numbers in Israel. Tried to send to number: ' + str(phone))

    phone_e164 = phonenumbers.format_number(phone, phonenumbers.PhoneNumberFormat.E164)

    # Strip the leading plus:
    phone_final = phone_e164[1:]

    smartsms_url = 'http://smartsms.co.il/member/http_sms_api.php'

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
        print message

    try:
        r = requests.post(smartsms_url, data=payload)
        r.raise_for_status()
    except requests.exceptions.RequestException as e:
        log_error(str(e))
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
