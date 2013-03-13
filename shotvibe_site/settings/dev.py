# Copy this file to settings_local.py and then edit it

# Make sure to keep DEBUG False for production
DEBUG = True
TEMPLATE_DEBUG = DEBUG

# Recommended database is PostgreSQL using postgresql_psycopg2 engine
# sqlite3 also works and is useful for development, the following will work out of the box:

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'test_databases/default.sqlite',                   # Or path to database file if using sqlite3.
        'USER': '',                             # Not used with sqlite3.
        'PASSWORD': '',                         # Not used with sqlite3.
        'HOST': '',                             # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                             # Set to empty string for default. Not used with sqlite3.
    }
}

# Make this unique, and don't share it with anybody.
SECRET_KEY = '!d*b0kzmxdg-!d=o^!8j#cr6^e666e$#wm0!m(uk3d&ix2)2sf'

LOCAL_PHOTO_BUCKETS_BASE_PATH = 'photo_buckets'
LOCAL_PHOTO_BUCKET_URL_FORMAT_STR = '/photos/{0}/{1}.jpg'

# import sys
# settings = sys.modules['shotvibe_site.settings.settings']
# ROOT_URLCONF = settings.SUBDOMAIN_URLCONFS['api']


AUTHENTICATION_BACKENDS = ('phone_auth.backend.DummyAuthBackend', 'phone_auth.backend.UserBackend')
