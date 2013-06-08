from django.shortcuts import render_to_response
from django.template import RequestContext
from django.http.response import HttpResponseNotFound

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
        test_app_url = 'market://details?id=com.urbandictionary.android'
    elif device == 'iphone':
        test_app_url = 'itms-apps://itunes.apple.com/us/app/urban-dictionary/id584986228'
    else:
        test_app_url = None

    data = {
            'inviting_user' : link_code_object.inviting_user,
            'album' : album,
            'app_url' : test_app_url,
            'device' : device }
    return render_to_response('frontend/mobile/invite_page.html', data, context_instance=RequestContext(request))

def get_device(ua):
    if ua.find('iphone') > 0:
        return 'iphone'

    if ua.find('android') > 0:
        return 'android'

    return 'other'
