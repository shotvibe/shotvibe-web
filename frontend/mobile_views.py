from django.shortcuts import render_to_response
from django.template import RequestContext

from photos.models import Album

def invite_page(request, invite_code):
    test_user = { 'get_full_name': 'Benny' }
    test_album = Album.objects.get(pk=5)

    device = get_device(request.META.get('HTTP_USER_AGENT', '').lower())

    if device == 'android':
        test_app_url = 'market://details?id=com.urbandictionary.android'
    elif device == 'iphone':
        test_app_url = 'itms-apps://itunes.apple.com/us/app/urban-dictionary/id584986228'
    else:
        test_app_url = None

    data = {
            'inviting_user' : test_user,
            'album' : test_album,
            'app_url' : test_app_url,
            'device' : device }
    return render_to_response('frontend/mobile/invite_page.html', data, context_instance=RequestContext(request))

def get_device(ua):
    if ua.find('iphone') > 0:
        return 'iphone'

    if ua.find('android') > 0:
        return 'android'

    return 'other'
