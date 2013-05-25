from django.http import HttpResponseNotFound, HttpResponse
from django.utils import timezone

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from phone_auth.serializers import AuthorizePhoneNumberSerializer, ConfirmSMSCodeSerializer

from phone_auth.models import AuthToken, PhoneNumber

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

# This view is called from the mobile app, after it has been installed, and is
# being run for the first time
def app_init(request):
    app = request.GET.get('app', 'unknown')

    if not app in ['android', 'iphone']:
        # This should never happen from a valid app
        # TODO Maybe log this or something
        return HttpResponseNotFound('Unknown app', content_type='text/plain')

    # TODO This should determine the user's country using a GeoIP lookup
    country_code = 'US'

    response = HttpResponse(status=302)

    try:
        phone_number_str = request.session['phone_number']
    except KeyError:
        # There was no 'phone_number' session data, so this means that the app
        # has been installed manually by the user, without going through an
        # invite link. The user will have to register with his phone number
        # inside the app. We still give the app the user's country_code, to
        # make it easier for him to enter his phone number.
        if app == 'android':
            response['Location'] = 'shotvibe://shotvibe/start_unregistered/?country_code=' + country_code
        elif app == 'iphone':
            response['Location'] = 'shotvibe://shotvibe/start_unregistered/?country_code=' + country_code

        return response

    # TODO If the 'phone_number' session data exists, then there should always
    # be a matching PhoneNumber. But just in case there isn't, maybe we should
    # handle it as above
    phone_number = PhoneNumber.objects.get(phone_number=phone_number_str)
    user = phone_number.user

    device_description = request.GET.get('device_description', 'unknown')

    auth_token = AuthToken.objects.create_auth_token(user, device_description, timezone.now())

    # TODO Probably should PhoneNumberLinkCode.objects.get(user=user).delete()
    # and also the 'phone_number' session data

    if app == 'android':
        response['Location'] = 'shotvibe://shotvibe/start_with_auth/?country_code=' + country_code + '&auth_token=' + auth_token.key + '&user_id=' + str(user.id)
    elif app == 'iphone':
        response['Location'] = 'shotvibe://shotvibe/start_with_auth/?country_code=' + country_code + '&auth_token=' + auth_token.key + '&user_id=' + str(user.id)

    return response
