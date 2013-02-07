from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from phone_auth.serializers import AuthorizePhoneNumberSerializer, ConfirmSMSCodeSerializer

from phone_auth.models import PhoneNumber

class AuthorizePhoneNumber(APIView):
    serializer_class = AuthorizePhoneNumberSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.DATA)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        phone_number_str = serializer.object['phone_number_str']

        confirmation_key = PhoneNumber.objects.authorize_phone_number(phone_number_str)

        return Response({ 'confirmation_key': confirmation_key })

class ConfirmSMSCode(APIView):
    serializer_class = ConfirmSMSCodeSerializer

    def post(self, request, confirmation_key):
        serializer = self.serializer_class(data=request.DATA)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        result = PhoneNumber.objects.confirm_phone_number(
                confirmation_key,
                serializer.object['confirmation_code'],
                serializer.object['device_description'])

        if not result.success:
            if result.incorrect_code:
                return Response({ 'detail': '"confirmation_code" is incorrect. Please try again.' }, status=status.HTTP_403_FORBIDDEN)
            elif result.expired_key:
                return Response({ 'detail': '"confirmation_key" has expired. Please request a new one.' }, status=status.HTTP_410_GONE)
            else:
                raise NotImplementedError('Unknown failure')

        return Response({
            'user_id': result.user.id,
            'auth_token': result.auth_token
            })
