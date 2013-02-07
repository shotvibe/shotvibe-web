from rest_framework import serializers

import phonenumbers

class AuthorizePhoneNumberSerializer(serializers.Serializer):
    phone_number = serializers.CharField()
    default_country = serializers.CharField(min_length=2, max_length=2)

    def validate(self, attrs):
        phone_number = attrs.get('phone_number')
        default_country = attrs.get('default_country')

        try:
            number = phonenumbers.parse(phone_number, default_country)
        except phonenumbers.phonenumberutil.NumberParseException as e:
            raise serializers.ValidationError(unicode(e))

        if not phonenumbers.is_possible_number(number):
            raise serializers.ValidationError('Phone number is invalid')

        attrs['phone_number_str'] = phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.E164)
        return attrs

class ConfirmSMSCodeSerializer(serializers.Serializer):
    confirmation_code = serializers.CharField()
    device_description = serializers.CharField()
