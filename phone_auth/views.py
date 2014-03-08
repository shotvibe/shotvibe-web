from django.conf import settings
from django.contrib.gis.geoip import GeoIP, GeoIPException
from django.http import HttpResponseNotFound, HttpResponse
from django.utils import timezone
from django.views.decorators.cache import never_cache

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from phone_auth.serializers import AuthorizePhoneNumberSerializer, ConfirmSMSCodeSerializer

from phone_auth.models import AuthToken, PhoneNumber, PhoneNumberLinkCode
from affiliates.models import Event

from photos.models import Album
from phone_auth.models import User
from photos_api.serializers import MemberIdentifier

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

        custom_payload = request.GET.get('custom_payload')
        if custom_payload:
            if custom_payload == 'dolev-event-2014-01-24':
                eventAlbum = Album.objects.get(id=1361)

                inviter = User.objects.get(id=475535083)
                eventAlbum.add_members(inviter, [MemberIdentifier(user_id=result.user.id)])

        return Response({
            'user_id': result.user.id,
            'auth_token': result.auth_token
            })

@api_view(['POST'])
@permission_classes((IsAuthenticated,))
def logout(request):
    assert isinstance(request.auth, AuthToken)
    request.auth.logout()

    return Response()

@api_view(['POST'])
@permission_classes((IsAuthenticated,))
def delete_account(request):
    """
    This function is very dangerous!

    It will delete the user account and all associated data, including:
    - All photos added
    - All albums created, including all of the contained photos, even if other users added them!
    """
    request.user.delete()

    return Response()

# This view is called from the mobile app, after it has been installed, and is
# being run for the first time
@never_cache
def app_init(request):
    app = request.GET.get('app', 'unknown')

    if not app in ['android', 'iphone']:
        # This should never happen from a valid app
        # TODO Maybe log this or something
        return HttpResponseNotFound('Unknown app', content_type='text/plain')

    country_code = None
    try:
        g = GeoIP()
        country_code = g.country_code(request.META.get('REMOTE_ADDR'))
        del g
    except GeoIPException:
        pass

    if country_code is None:
        country_code = 'US'

    app_url_scheme = request.GET.get('app_url_scheme', 'shotvibe')

    response = HttpResponse(status=302)

    phone_number_str = request.session.get('phone_number')
    event_str = request.session.get('event')

    if event_str and not phone_number_str:
        # There was no 'phone_number' session data, but an 'event' and 'album' was set.
        # This means this user came in through an affiliate link.
        try:
            event = Event.objects.get(pk=event_str)
        except Event.DoesNotExist:
            del request.session['event']
        else:
            if app == 'android':
                response['Location'] = app_url_scheme + '://shotvibe/start_from_event/?country_code=' + country_code + '&event_id=' + str(event.pk) + '&album_id=' + str(event.album.pk)
            elif app == 'iphone':
                response['Location'] = app_url_scheme + '://shotvibe/start_from_event/?country_code=' + country_code + '&event_id=' + str(event.pk) + '&album_id=' + str(event.album.pk)
            return response

    if phone_number_str is None:
        # There was no 'phone_number' session data, so this means that the app
        # has been installed manually by the user, without going through an
        # invite link. The user will have to register with his phone number
        # inside the app. We still give the app the user's country_code, to
        # make it easier for him to enter his phone number.

        custom_payload = request.session.get('custom_payload')
        if custom_payload:
            if app == 'android':
                response['Location'] = app_url_scheme + '://shotvibe/start_unregistered/?country_code=' + country_code + '&custom_payload=' + custom_payload
            elif app == 'iphone':
                response['Location'] = app_url_scheme + '://shotvibe/start_unregistered/?country_code=' + country_code + '&custom_payload=' + custom_payload

            return response

        if app == 'android':
            response['Location'] = app_url_scheme + '://shotvibe/start_unregistered/?country_code=' + country_code
        elif app == 'iphone':
            response['Location'] = app_url_scheme + '://shotvibe/start_unregistered/?country_code=' + country_code

        return response

    # TODO If the 'phone_number' session data exists, then there should always
    # be a matching PhoneNumber. But just in case there isn't, maybe we should
    # handle it as above
    phone_number = PhoneNumber.objects.get(phone_number=phone_number_str)
    user = phone_number.user

    device_description = request.GET.get('device_description', 'unknown')

    phone_number.verified = True
    phone_number.save(update_fields=['verified'])

    auth_token = AuthToken.objects.create_auth_token(user, device_description, timezone.now())

    PhoneNumberLinkCode.objects.filter(phone_number=phone_number).delete()
    if len(request.session.keys()) > 1:
        # There is some other session data besides 'phone_number', so only
        # selectively delete
        del request.session['phone_number']
    else:
        # Only 'phone_number' was in the session data, so we can delete the
        # entire session
        response.delete_cookie(
                settings.SESSION_COOKIE_NAME,
                settings.SESSION_COOKIE_PATH,
                settings.SESSION_COOKIE_DOMAIN)
        request.session.delete()

    if app == 'android':
        response['Location'] = app_url_scheme + '://shotvibe/start_with_auth/?country_code=' + country_code + '&auth_token=' + auth_token.key + '&user_id=' + str(user.id)
    elif app == 'iphone':
        response['Location'] = app_url_scheme + '://shotvibe/start_with_auth/?country_code=' + country_code + '&auth_token=' + auth_token.key + '&user_id=' + str(user.id)

    return response

@never_cache
@api_view(['POST'])
def country_lookup(request):
    version = request.GET.get('version', '0')

    if version == settings.DISABLE_AUTOLOGIN_FOR_COUNTRY_LOOKUP_VERSION:
        country_code = None
        try:
            g = GeoIP()
            country_code = g.country_code(request.META.get('REMOTE_ADDR'))
            del g
        except GeoIPException:
            pass

        if country_code is None:
            country_code = 'US'
    else:
        COUNTRY_CODE_AUTOLOGIN = 'auto'

        country_code = COUNTRY_CODE_AUTOLOGIN

    response_data = {
            'country_code' : country_code
            }

    return Response(response_data)
