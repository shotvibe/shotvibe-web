import json
import requests

from django.conf import settings
from django.core import mail

from rest_framework import views
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

class GcmDevice(views.APIView):
    permission_classes = (IsAuthenticated,)

    def put(self, request, device_id, format=None):
        rq = { 'user_id' : str(request.user.id) }
        requests.put(settings.UNIVERSAL_PUSH_PROVIDER_URL + '/gcm/device/' + device_id, data=json.dumps(rq))
        return Response()

    def delete(self, request, device_id, format=None):
        requests.delete(settings.UNIVERSAL_PUSH_PROVIDER_URL + '/gcm/device/' + device_id)
        return Response()

class ApnsDevice(views.APIView):
    pass

def in_testing_mode():
    # An evil hack to detect if we are running unit tests
    # http://stackoverflow.com/questions/6957016/detect-django-testing-mode
    return hasattr(mail, 'outbox')

def send_message_or_log_errors(msg):
    if in_testing_mode():
        return

    try:
        r = requests.post(settings.UNIVERSAL_PUSH_PROVIDER_URL + '/send', data=json.dumps(msg))
        r.raise_for_status()
    except requests.exceptions.RequestException as e:
        # TODO better logging
        print 'Error sending push notification: ' + str(e)

def broadcast_photos_added(album_id, author_id, album_name, author_name, num_photos, user_ids):
    # Send broadcast to all other users
    rq = {
            'user_ids' : [str(id) for id in user_ids if id != author_id],
            'gcm' : {
                'data' : {
                    'type' : 'photos_added',
                    'album_id' : str(album_id),
                    'author' : author_name,
                    'album_name' : album_name,
                    'num_photos' : str(num_photos)
                    }
                },
            'apns' : {
                'aps' : {
                    'alert' : author_name + ' added ' + str(num_photos) + ' photos to the album ' + album_name,
                    },
                'album_id' : album_id
                }
            }
    send_message_or_log_errors(rq)

    # Send broadcast to the author, so that all of his devices will sync
    rq = { 'user_ids' : [str(author_id)],
            'gcm' : {
                'data' : {
                    'type' : 'album_sync',
                    'album_id' : str(album_id)
                    }
                },
            'apns' : {
                'aps' : {
                    'alert' : None
                    },
                'album_id' : album_id
                }
            }
    send_message_or_log_errors(rq)
