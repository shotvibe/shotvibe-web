"""
Settings used for Jenkins builds
"""

import os
import sys

DEBUG = False
TEMPLATE_DEBUG = DEBUG

try:
    JENKINS_DATABASE_NAME = os.environ['JENKINS_DATABASE_NAME']
    JENKINS_DATABASE_USER = os.environ['JENKINS_DATABASE_USER']
    JENKINS_DATABASE_PASSWORD = os.environ['JENKINS_DATABASE_PASSWORD']
except KeyError:
    print '*** You must set the needed environment variables'
    raise

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': JENKINS_DATABASE_NAME,
        'USER': JENKINS_DATABASE_USER,
        'PASSWORD': JENKINS_DATABASE_PASSWORD,
        'HOST': 'localhost',
        'PORT': '',
    }
}

# Make this unique, and don't share it with anybody.
SECRET_KEY = '!d*b0kzmxdg-!d=o^!8j#cr6^e666e$#wm0!m(uk3d&ix2)2sf'

LOCAL_PHOTO_BUCKETS_BASE_PATH = 'photo_buckets'
LOCAL_PHOTO_BUCKET_URL_FORMAT_STR = '/photos/{0}/{1}.jpg'

INSTALLED_APPS = sys.modules['shotvibe_site.settings'].INSTALLED_APPS + (
    'django_extensions',
    'django_jenkins',
)

JENKINS_TASKS = (
    'django_jenkins.tasks.run_sloccount',
    'django_jenkins.tasks.with_coverage',
    'django_jenkins.tasks.django_tests',
    'django_jenkins.tasks.run_graphmodels',
)

PROJECT_APPS = (
    'frontend',
    'photos',
    'phone_auth',
    'photos_api',
)
