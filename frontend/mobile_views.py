from django.shortcuts import render_to_response
from django.template import RequestContext

from photos.models import Album

def invite_page(request, invite_code):
    test_user = { 'get_full_name': 'Benny' }
    test_album = Album.objects.get(pk=5)

    ua = request.META.get('HTTP_USER_AGENT', '').lower()
    test_app_url = 'market://details?id=com.urbandictionary.android'

    data = {
            'inviting_user' : test_user,
            'album' : test_album,
            'app_url' : test_app_url,
            'full_user_agent' : ua }
    return render_to_response('frontend/mobile/invite_page.html', data, context_instance=RequestContext(request))
