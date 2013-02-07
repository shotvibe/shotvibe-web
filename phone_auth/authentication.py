from rest_framework import authentication

from phone_auth.models import AuthToken

class TokenAuthentication(authentication.TokenAuthentication):
    model = AuthToken
