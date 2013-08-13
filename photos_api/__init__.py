import re

MOBILE_NUMBER_REGEXES = {
    'IL': re.compile(r'^\+972(54|52|50|58).+?$')
}

def is_phone_number_mobile(phone_number_str, country_code):
    """Returns True if given phone number is mobile"""

    # Non-IL phones are temporarily mobile.
    if country_code not in MOBILE_NUMBER_REGEXES:
        return True

    regex = MOBILE_NUMBER_REGEXES.get(country_code)
    return regex.match(phone_number_str)
