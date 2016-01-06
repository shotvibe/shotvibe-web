from rest_framework import authentication

from phone_auth.models import AuthToken

class TokenAuthentication(authentication.TokenAuthentication):
    model = AuthToken

    def authenticate(self, request):
        result = super(TokenAuthentication, self).authenticate(request)
        if result:
            (user, auth) = result

            # This is a bit of a hack. We need to store this, so we can use it
            # later in phone_auth.middleware.LastOnlineMiddleware
            #
            # `request` is the rest_framework Request object, and the
            # `_request` field is the original Django Request object (which we
            # will later have access to in the middleware `process_response`
            # method
            request._request.shotvibe_user = user
        return result
