import HTMLParser

import phonenumbers
import requests

from django.conf import settings

COUNTRY_CODE_ISRAEL = 972

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
