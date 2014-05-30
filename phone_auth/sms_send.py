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


def mark_sms_test_case(testcase_class):
    """
    Should be used as a decorator on a class (that derives from Django's TestCase)

    Makes sure that the SMS testing outbox is cleared before each test runs
    """
    orig_pre_setup = testcase_class._pre_setup

    def _pre_setup(self):
        # Clear the SMS testing outbox before each test runs
        send_sms.testing_outbox = []
        orig_pre_setup(self)

    testcase_class._pre_setup = _pre_setup
    return testcase_class


def send_sms(destination_phone, message, sender_phone=None):
    """
    destination_phone must be formatted as international E164

    sender_phone must be formatted as international E164, or it may be "None"
    Note that the system will make a "best effort" to make the SMS appear to be
    sent from sender_phone, but it may not succeed
    """
    p = phonenumbers.parse(destination_phone)

    if in_testing_mode():
        # During unit tests, don't actually send any SMS messages. Instead,
        # keep a record of sent SMS's in the testing outbox
        if hasattr(send_sms, 'testing_outbox'):
            send_sms.testing_outbox.append((destination_phone, message, sender_phone))
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

    smartsms_url = 'http://www.smartsms.co.il/member/http_sms_xml_api.php?function=singles'

    if sender_phone:
        # Strip the leading plus:
        source_phone_number = sender_phone[1:]
    else:
        # This can be any phone number:
        source_phone_number = 'GLANCE'

    username = settings.SMARTSMS_CREDENTIALS['username']
    password = settings.SMARTSMS_CREDENTIALS['password']

    def create_request_doc():
        import xml.etree.ElementTree as ET

        # Example of a request document:
        #
        #   <Request>
        #     <UserName>{MyApiUserName}</UserName>
        #     <Password>{MyApiPassword}</Password>
        #     <Time>{1437282993}</Time>
        #     <Singles>
        #       <Single>
        #         <Message>{Message Text1}></Message>
        #         <DestinationNumber>{0549999999}</DestinationNumber>
        #         <SourceNumber>{0739999999}</SourceNumber>
        #         <ClientReference>{1000}</ClientReference>
        #       </Single>
        #     </Singles>
        #   </Request>

        e_Request = ET.Element('Request')
        e_UserName = ET.SubElement(e_Request, 'UserName')
        e_UserName.text = username
        e_Password = ET.SubElement(e_Request, 'Password')
        e_Password.text = password
        e_Time = ET.SubElement(e_Request, 'Time')
        e_Time.text = '0'
        e_Singles = ET.SubElement(e_Request, 'Singles')
        e_Single = ET.SubElement(e_Singles, 'Single')
        e_Message = ET.SubElement(e_Single, 'Message')
        e_Message.text = message
        e_SourceNumber = ET.SubElement(e_Single, 'SourceNumber')
        e_SourceNumber.text = source_phone_number
        e_DestinationNumber = ET.SubElement(e_Single, 'DestinationNumber')
        e_DestinationNumber.text = phone_final
        e_ClientReference = ET.SubElement(e_Single, 'ClientReference')
        e_ClientReference.text = '0'
        return ET.tostring(e_Request)

    payload = {
            'xml': create_request_doc()
            }

    def log_error(message):
        # TODO Better logging ...
        print message.encode('utf8')

    class SmartsmsResponse(object):
        RESPONSE_SUCCESS, \
                RESPONSE_XML_PARSE_ERROR, \
                RESPONSE_ERROR_CODE, \
                RESPONSE_INVALID_DESTINATION_NUMBER = range(4)

    def parse_response_doc(response_content):
        """
        Returns a tuple. First element is one of the constants in
        SmartsmsResponse. Second element is a string containing more detail
        """
        import xml.etree.ElementTree as ET

        # Example of a response doc for a successful request:
        #
        #   <Response>
        #     <SinglesResults>
        #       <SingleResult>
        #         <ServerId>5620979</ServerId>
        #         <ClientReference>0</ClientReference>
        #       </SingleResult>
        #     </SinglesResults>
        #   </Response>
        #
        # Example of a response doc for an unsuccessful request:
        #
        #   <?xml version="1.0" encoding="UTF-8" ?>
        #   <Response>
        #     <ErrorCode>BAD_CREDENTIALS</ErrorCode>
        #   </Response>

        try:
            root = ET.fromstring(response_content)
        except ET.ParseError as e:
            return SmartsmsResponse.RESPONSE_XML_PARSE_ERROR, unicode(e)
        if root.tag != 'Response':
            return SmartsmsResponse.RESPONSE_XML_PARSE_ERROR, 'Root Xml element is not <Response>. It is: <' + root.tag + '>'
        for child in root:
            if child.tag == 'ErrorCode':
                return SmartsmsResponse.RESPONSE_ERROR_CODE, child.text
            elif child.tag == 'SinglesResults':
                for result in child:
                    if result.tag == 'SingleResult':
                        return SmartsmsResponse.RESPONSE_SUCCESS, None
        return SmartsmsResponse.RESPONSE_INVALID_DESTINATION_NUMBER, ''

    try:
        r = requests.post(smartsms_url, data=payload)
        r.raise_for_status()
    except requests.exceptions.RequestException as e:
        log_error(unicode(e))

    response, detail = parse_response_doc(r.content)
    if response == SmartsmsResponse.RESPONSE_SUCCESS:
        return
    elif response == SmartsmsResponse.RESPONSE_XML_PARSE_ERROR:
        log_error(unicode(detail))
        return
    elif response == SmartsmsResponse.RESPONSE_ERROR_CODE:
        log_error(unicode(detail))
        return
    elif response == SmartsmsResponse.RESPONSE_INVALID_DESTINATION_NUMBER:
        log_error('The destination phone is unable to receive SMS messages: ' + phone_final)
        return
