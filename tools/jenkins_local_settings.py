"""
Settings used for Jenkins builds
"""

import os
import sys

parent_settings = sys.modules['shotvibe_site.settings']

DEBUG = False
TEMPLATE_DEBUG = DEBUG

try:
    JENKINS_DATABASE_NAME = os.environ['JENKINS_DATABASE_NAME']
    JENKINS_DATABASE_USER = os.environ['JENKINS_DATABASE_USER']
    JENKINS_DATABASE_PASSWORD = os.environ['JENKINS_DATABASE_PASSWORD']
except KeyError:
    print '*** You must set the needed environment variables'
    raise

parent_settings.DATABASES['default']['ENGINE'] = 'django.db.backends.postgresql_psycopg2'
parent_settings.DATABASES['default']['NAME'] = JENKINS_DATABASE_NAME
parent_settings.DATABASES['default']['USER'] = JENKINS_DATABASE_USER
parent_settings.DATABASES['default']['PASSWORD'] = JENKINS_DATABASE_PASSWORD
parent_settings.DATABASES['default']['HOST'] = 'localhost'
parent_settings.DATABASES['default']['PORT'] = ''

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

# Buckets where we upload new avatars
AVATAR_BUCKETS = (
    's3:shotvibe-avatars-01:{filename}',
    's3:shotvibe-avatars-02:{filename}'
)

# Format string for user avatar files. It should contain keyword argiments
# `user_id` and `timestamp`.
AVATAR_FILENAME_FORMAT_STRING = "user-avatar-{user_id}-{timestamp}.jpg"

# Map of Storage:URL_Format_String for avatar images.
# This is used to construct URL for a user's avatar from internal
# representation storage:bucket_name:filename.
AVATAR_STORAGE_URL_FORMAT_STRING_MAP = {
    's3': 'https://{bucket_name}.s3.amazonaws.com/{filename}'
}

# Data required to generate default avatar file.
# (format_string, min_number, max_number)
DEFAULT_AVATAR_FILES = [
    ('s3:shotvibe-avatars-01:default-avatar-{0:04d}.jpg', 1, 78),
    # ('foo:bar2:avatar_{0}', 41, 78)
]

# AWS Credentials
AWS_ACCESS_KEY = "AKIAJ37YWEH3ZXFSVQ2A"
AWS_SECRET_ACCESS_KEY = "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"
