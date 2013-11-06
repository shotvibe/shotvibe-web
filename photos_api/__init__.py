import phonenumbers

COUNTRY_CODE_IL = 972

def is_phone_number_mobile(number):
    """Returns True if given phone number is mobile"""

    country_checkers = {
            COUNTRY_CODE_IL: is_phone_number_mobile_IL
            }

    checker = country_checkers.get(number.country_code, None)
    if checker:
        return checker(number)
    else:
        # For any countries that we don't know how to check, we assume that the
        # number is mobile
        return True


def is_phone_number_mobile_IL(number):
    phone_e164 = phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.E164)

    # These are all of the mobile operators in Israel:

    if phone_e164.startswith('+97250'): # Pelephone
        return True
    if phone_e164.startswith('+97252'): # Cellcom
        return True
    if phone_e164.startswith('+97253'): # Hot Mobile
        return True
    if phone_e164.startswith('+97257'): # Hot Mobile (Formerly Mirs)
        return True
    if phone_e164.startswith('+97254'): # Partner
        return True
    if phone_e164.startswith('+97255'): # Virtual operators: Rami Levy, Alon Cellular, Home Cellular
        return True
    if phone_e164.startswith('+97258'): # Golan Telecom
        return True

    # Not a mobile operator, must be a landline:
    return False
