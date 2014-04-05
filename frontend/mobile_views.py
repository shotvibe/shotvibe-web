from django.conf import settings
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.http import HttpResponse
from django.http.response import HttpResponseNotFound

from subdomains.utils import reverse

from phone_auth.models import PhoneNumberLinkCode
from photos.models import Album

from affiliates.models import Event
from frontend.user_device import get_device


def invite_page(request, invite_code):
    try:
        link_code_object = PhoneNumberLinkCode.objects.get(pk=invite_code)
    except PhoneNumberLinkCode.DoesNotExist:
        # TODO Return a generic page that explains that the invite link has
        # expired, and inviting the user to install the app anyway
        return HttpResponseNotFound()

    # For showing the album, just grab the first album that the user belongs to
    album = Album.objects.get_user_albums(link_code_object.phone_number.user.id)[0]

    device = get_device(request.META.get('HTTP_USER_AGENT', ''))

    request.session['phone_number'] = link_code_object.phone_number.phone_number

    if device.os == 'android':
        app_url = settings.GOOGLE_PLAY_URL
    elif device.os == 'iphone':
        app_url = settings.APPLE_APP_STORE_URL
    else:
        app_url = None

    link_code_object.was_visited = True
    link_code_object.save(update_fields=['was_visited'])

    # Check if this album is part of an event
    try:
        event = Event.objects.get(album=album)
        # The album is part of an event. Show the invite page in the style of
        # an event invite:
        data = {
                'event': event,
                'album': album,
                'app_url': app_url,
                'device': device }
    except Event.DoesNotExist:
        # The album is not part of an event. Show the invite page in the style of
        # a personal invite:
        data = {
                'inviting_user' : link_code_object.inviting_user,
                'album' : album,
                'app_url' : app_url,
                'device' : device }


    return render_to_response('frontend/mobile/invite_page.html', data, context_instance=RequestContext(request))


def get_app(request):
    device = get_device(request.META.get('HTTP_USER_AGENT', ''))

    if device.os == 'android':
        app_url = settings.GOOGLE_PLAY_URL
    elif device.os == 'iphone':
        app_url = settings.APPLE_APP_STORE_URL
    else:
        # neither android or iphone, redirect user to the home page
        app_url = reverse('index', subdomain='www', scheme='https')

    response = HttpResponse(status=302)
    response['Location'] = app_url
    return response
