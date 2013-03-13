from .settings import *
ROOT_URLCONF = SUBDOMAIN_URLCONFS['api']

AUTHENTICATION_BACKENDS = ('phone_auth.backend.DummyAuthBackend', 'phone_auth.backend.UserBackend')
