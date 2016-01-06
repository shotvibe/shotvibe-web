from django.utils import timezone

class LastOnlineMiddleware(object):
    def process_response(self, request, response):
        # The `shotvibe_user` field is set during authentication in
        # phone_auth.authentication.TokenAuthentication
        if hasattr(request, 'shotvibe_user') and request.shotvibe_user and not request.shotvibe_user.is_anonymous():
            request.shotvibe_user.set_last_online(timezone.now())
        return response
