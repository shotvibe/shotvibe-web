from django.utils import timezone

from rest_framework import authentication

from phone_auth.models import AuthToken

def update_user_last_online(user):
    if not user.is_anonymous():
        user.last_online = timezone.now()
        user.save(update_fields=['last_online'])

class TokenAuthentication(authentication.TokenAuthentication):
    model = AuthToken

    def authenticate(self, request):
        result = super(TokenAuthentication, self).authenticate(request)
        if result:
            (user, auth) = result
            # We do this here in the authentication, rather than in a Django
            # middleware, because middleware is run before Django Rest
            # Framework authentication is performed
            update_user_last_online(user)
        return result
