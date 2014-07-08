import json
import requests

from django.conf import settings
from django.contrib import admin
from django.contrib import auth
from django.core import mail
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.core.exceptions import ObjectDoesNotExist

from rest_framework import status
from rest_framework import views
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

@api_view(['POST'])
@permission_classes((IsAuthenticated, ))
def register_device_push(request):
    try:
        device = json.loads(request.stream.body)
    except ValueError as ex:
        return Response({ 'error': str(ex) }, status=status.HTTP_400_BAD_REQUEST)

    rq = {
            'user_id': str(request.user.id),
            'device': device
            }

    # TODO Once we add an "id" field to phone_auth.AuthToken:
    # rq['user_auth'] = str(request.auth.id)

    r = requests.post(settings.UNIVERSAL_PUSH_PROVIDER_URL + '/device/register', data=json.dumps(rq))
    r.raise_for_status()

    return Response(None, status=status.HTTP_204_NO_CONTENT)

# This is deprecated:
class GcmDevice(views.APIView):
    permission_classes = (IsAuthenticated,)

    def put(self, request, device_id, format=None):
        rq = { 'user_id' : str(request.user.id) }
        requests.put(settings.UNIVERSAL_PUSH_PROVIDER_URL + '/gcm/device/' + device_id, data=json.dumps(rq))
        return Response()

    def delete(self, request, device_id, format=None):
        requests.delete(settings.UNIVERSAL_PUSH_PROVIDER_URL + '/gcm/device/' + device_id)
        return Response()

@admin.site.admin_view
def upp_status(request):
    if 'gcm_config_set' in request.POST:
        api_key = request.POST['gcm_api_key']
        rq = { 'api_key' : api_key }
        r = requests.put(settings.UNIVERSAL_PUSH_PROVIDER_URL + '/gcm/api_key', data=json.dumps(rq))
        r.raise_for_status()

    if 'send_push_message' in request.POST:
        user_ids = request.POST.getlist('user_id')
        message = request.POST['message_text']
        rq = {
                'user_ids' : user_ids,
                'gcm' : {
                    'data' : {
                        'type' : 'test_message',
                        'message' : message
                        }
                    },
                'apns' : {
                    'aps' : {
                        'alert' : 'Test Message: ' + message,
                        'sound': 'default'
                        }
                    }
                }
        r = requests.post(settings.UNIVERSAL_PUSH_PROVIDER_URL + '/send', data=json.dumps(rq))
        r.raise_for_status()

    r = requests.get(settings.UNIVERSAL_PUSH_PROVIDER_URL + '/status')
    status = json.loads(r.text)

    resolved_user_devices = {}
    unknown_user_ids = []

    for user_id, devices in status['user_devices'].iteritems():
        try:
            user = auth.get_user_model().objects.get(pk=user_id)
            resolved_user_devices[user] = devices
        except ObjectDoesNotExist:
            unknown_user_ids.append(user_id)

    data = {
            'database_info': status['database_info'],
            'gcm_config': status['gcm_config'],
            'user_devices': resolved_user_devices,
            'unknown_user_ids': unknown_user_ids
            }

    return render_to_response('upp_status.html', data, context_instance=RequestContext(request))

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

def broadcast_photos_added_to_album(album_id, author_id, album_name, author_name, num_photos, user_ids):
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
                    'sound': 'default'
                    },

                # TODO More Data needed

                'album_id' : album_id
                }
            }
    send_message_or_log_errors(rq)


def broadcast_members_added_to_album(album_id, album_name, adder_name, user_ids):
    rq = {
            'user_ids': [str(id) for id in user_ids],
            'gcm': {
                'data': {
                    'type': 'added_to_album',
                    'album_id': str(album_id),
                    'adder': adder_name,
                    'album_name' : album_name,
                    }
                },
            'apns': {
                'aps': {
                    'alert': adder_name + ' added you to the album ' + album_name,
                    'sound': 'default'
                    },

                # TODO More Data needed

                'album_id': album_id
                }
            }
    send_message_or_log_errors(rq)

def broadcast_album_list_sync(user_ids):
    _user_ids = []
    if type(user_ids) in [tuple, list]:
        _user_ids = [str(id) for id in user_ids]
    else:
        _user_ids = [str(user_ids)]
    rq = {
            'user_ids': _user_ids,
            'gcm': {
                'data': {
                    'type': 'album_list_sync'
                    }
                },
            'apns': {
                'aps': {},
                'type': 'album_list_sync'
                }
            }
    send_message_or_log_errors(rq)

def broadcast_album_sync(user_ids, album_id):
    _user_ids = []
    if type(user_ids) in [tuple, list]:
        _user_ids = [str(id) for id in user_ids]
    else:
        _user_ids = [str(user_ids)]
    # Send broadcast to the author, so that all of his devices will sync
    rq = { 'user_ids' : _user_ids,
            'gcm' : {
                'data' : {
                    'type' : 'album_sync',
                    'album_id' : str(album_id)
                    }
                },
            'apns' : {
                'aps' : {},
                'type': 'album_sync',
                'album_id' : album_id
                }
            }
    send_message_or_log_errors(rq)


def broadcast_photo_glance(author_id, glance_user_name, album_id, album_name):
    payload = {
            'type': 'photo_glance',
            'album_id': album_id,
            'album_name': album_name,
            'user_nickname': glance_user_name
        }

    rq = {
            'user_ids': [str(author_id)],
            'gcm': {
                'data': {
                    'd': json.dumps(payload)
                    }
                },
            'apns': {
                'aps': {
                    'alert': glance_user_name + ' glanced your photo in ' + album_name,
                    'sound': 'default'
                    }
                }
            }
    send_message_or_log_errors(rq)
