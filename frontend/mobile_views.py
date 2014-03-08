from django.conf import settings
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.http.response import HttpResponseNotFound, HttpResponse

from phone_auth.models import PhoneNumberLinkCode
from photos.models import Album

def invite_page(request, invite_code):
    try:
        link_code_object = PhoneNumberLinkCode.objects.get(pk=invite_code)
    except PhoneNumberLinkCode.DoesNotExist:
        # TODO Return a generic page that explains that the invite link has
        # expired, and inviting the user to install the app anyway
        return HttpResponseNotFound()

    # For showing the album, just grab the first album that the user belongs to
    album = Album.objects.get_user_albums(link_code_object.phone_number.user.id)[0]

    device = get_device(request.META.get('HTTP_USER_AGENT', '').lower())

    request.session['phone_number'] = link_code_object.phone_number.phone_number

    if device == 'android':
        app_url = settings.GOOGLE_PLAY_URL
    elif device == 'iphone':
        app_url = settings.APPLE_APP_STORE_URL
    else:
        app_url = None

    link_code_object.was_visited = True
    link_code_object.save(update_fields=['was_visited'])

    data = {
            'inviting_user' : link_code_object.inviting_user,
            'album' : album,
            'app_url' : app_url,
            'device' : device }
    return render_to_response('frontend/mobile/invite_page.html', data, context_instance=RequestContext(request))


# Temporary event for Dolev 2014-01-24
def dolev_event(request):
    device = get_device(request.META.get('HTTP_USER_AGENT', '').lower())

    if device == 'android':
        app_url = settings.GOOGLE_PLAY_URL
    elif device == 'iphone':
        app_url = settings.APPLE_APP_STORE_URL
    else:
        app_url = None

    if app_url:
        request.session['custom_payload'] = 'dolev-event-2014-01-24'

        response = HttpResponse("", status=302)
        response['Location'] = app_url
        return response

    return HttpResponse("You must open the link from your phone", content_type="text/plain")


def get_device(ua):
    if ua.find('iphone') > 0:
        return 'iphone'

    if ua.find('android') > 0:
        return 'android'

    return 'other'
