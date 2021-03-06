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
        payload = {
                'type': 'test_message',
                'message': message
            }
        rq = {
                'user_ids' : user_ids,
                'gcm' : {
                    'data' : {
                        'd': json.dumps(payload),

                        # Deprecated data:
                        'type' : 'test_message',
                        'message' : message
                        }
                    },
                'apns' : {
                    'aps' : {
                        'alert' : 'Test Message: ' + message,
                        'sound': 'default'
                        },
                    'd': payload
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

#
# Individual notification types:
#
def broadcast_photos_added_to_album(album_id, author_id, album_name, author_name, author_avatar_url, num_photos, user_ids,album_photo):
    payload = {
            'type': 'photos_added',
            'album_id': album_id,
            'author': author_name,
            'author_avatar_url': author_avatar_url,
            'album_name': album_name,
            'num_photos': num_photos,
            'photo_id' : album_photo
        }

    # Send broadcast to all other users
    rq = {
            'user_ids' : [str(id) for id in user_ids if id != author_id],
            'gcm' : {
                'data' : {
                    'd': json.dumps(payload),

                    # Deprecated data:
                    'type' : 'photos_added',
                    'album_id' : str(album_id),
                    'author' : author_name,
                    'album_name' : album_name,
                    'num_photos' : str(num_photos)
                    }
                },
            'apns' : {
                'aps' : {
                    'alert' : author_name + ' added ' + str(num_photos) + ' photos to the group ' + album_name,
                    'sound': 'push.mp3',
                    'badge': 1
                    },
                'd': payload
                }
            }
    send_message_or_log_errors(rq)

def broadcast_videos_added_to_album(album_id, author_id, album_name, author_name, author_avatar_url, num_photos, user_ids,album_photo):
    payload = {
            'type': 'photos_added',
            'album_id': album_id,
            'author': author_name,
            'author_avatar_url': author_avatar_url,
            'album_name': album_name,
            'num_photos': 0,
            'photo_id' : album_photo
        }

    # Send broadcast to all other users
    rq = {
            'user_ids' : [str(id) for id in user_ids if id != author_id],
            'gcm' : {
                'data' : {
                    'd': json.dumps(payload),

                    # Deprecated data:
                    'type' : 'photos_added',
                    'album_id' : str(album_id),
                    'author' : author_name,
                    'album_name' : album_name,
                    'num_photos' : str(num_photos)
                    }
                },
            'apns' : {
                'aps' : {
                    'alert' : author_name + ' added a video to the group ' + album_name,
                    'sound': 'push.mp3',
                    'badge': 1
                    },
                'd': payload
                }
            }
    send_message_or_log_errors(rq)


def broadcast_members_added_to_album(album_id, album_name, adder_name, adder_avatar_url, user_ids):
    payload = {
            'type': 'added_to_album',
            'album_id': album_id,
            'adder': adder_name,
            'adder_avatar_url': adder_avatar_url,
            'album_name': album_name
        }

    rq = {
            'user_ids': [str(id) for id in user_ids],
            'gcm': {
                'data': {
                    'd': json.dumps(payload),

                    # Deprecated data:
                    'type': 'added_to_album',
                    'album_id': str(album_id),
                    'adder': adder_name,
                    'album_name' : album_name,
                    }
                },
            'apns': {
                'aps': {
                    'alert': adder_name + ' added you to the group ' + album_name,
                    'sound': 'push.mp3',
                    'badge': 1
                    },
                'd': payload
                }
            }
    send_message_or_log_errors(rq)

def broadcast_album_list_sync(user_ids):
    payload = {
            'type': 'album_list_sync',
        }

    _user_ids = []
    if type(user_ids) in [tuple, list]:
        _user_ids = [str(id) for id in user_ids]
    else:
        _user_ids = [str(user_ids)]
    rq = {
            'user_ids': _user_ids,
            'gcm': {
                'data': {
                    'd': json.dumps(payload),

                    # Deprecated data:
                    'type': 'album_list_sync'
                    }
                },
            'apns': {
                'aps': {},
                'd': payload
                }
            }
    send_message_or_log_errors(rq)

def broadcast_album_sync(user_ids, album_id):
    payload = {
            'type': 'album_sync',
            'album_id': album_id,
        }

    _user_ids = []
    if type(user_ids) in [tuple, list]:
        _user_ids = [str(id) for id in user_ids]
    else:
        _user_ids = [str(user_ids)]
    # Send broadcast to the author, so that all of his devices will sync
    rq = { 'user_ids' : _user_ids,
            'gcm' : {
                'data' : {
                    'd': json.dumps(payload),

                    # Deprecated data:
                    'type' : 'album_sync',
                    'album_id' : str(album_id)
                    }
                },
            'apns' : {
                'aps' : {},
                'd': payload
                }
            }
    send_message_or_log_errors(rq)


def broadcast_photo_comment(comment_thread_author_ids, comment_author_nickname, comment_author_avatar_url, album_id, photo_id, album_name, comment_text):
    payload = {
            'type': 'photo_comment',
            'album_id': album_id,
            'photo_id': photo_id,
            'album_name': album_name,
            'comment_author_nickname': comment_author_nickname,
            'comment_author_avatar_url': comment_author_avatar_url,
            'comment_text': comment_text
        }

    rq = {
            'user_ids': [str(id) for id in comment_thread_author_ids],
            'gcm': {
                'data': {
                    'd': json.dumps(payload)
                    }
                },
            'apns': {
                'aps': {
                    'alert': comment_author_nickname + ' commented on a photo @ ' + album_name,
                    'sound': 'push.mp3',
                    'badge': 1
                    },
                'd': payload
                }
            }
    send_message_or_log_errors(rq)


def broadcast_photo_glance_score_delta(user_ids, glance_author_nickname, glance_author_avatar_url, album_id, photo_id, album_name, score_delta):
    payload = {
            'type': 'photo_glance_score_delta',
            'album_id': album_id,
            'photo_id': photo_id,
            'album_name': album_name,
            'glance_author_nickname': glance_author_nickname,
            'glance_author_avatar_url': glance_author_avatar_url,
            'score_delta': score_delta
        }

    if score_delta >= 0:
        alert_text = glance_author_nickname + ' glanced your image. You just won 3 points to your score. Keep glancing'
    else:
        alert_text = glance_author_nickname + ' unglanced your image. You just lost 3 points to your score. Better glancing next time'
    rq = {
            'user_ids': [str(id) for id in user_ids],
            'gcm': {
                'data': {
                    'd': json.dumps(payload)
                    }
                },
            'apns': {
                'aps': {
                    'alert': alert_text,
                    'sound': 'push.mp3',
                    'badge': 1
                    },
                'd': payload
                }
            }
    send_message_or_log_errors(rq)


def broadcast_photo_user_tagged(tagged_user_id, album_id, photo_id, album_name):
    payload = {
            'type': 'photo_user_tagged',
            'album_id': album_id,
            'photo_id': photo_id,
            'album_name': album_name,
        }

    rq = {
            'user_ids': [str(tagged_user_id)],
            'gcm': {
                'data': {
                    'd': json.dumps(payload)
                    }
                },
            'apns': {
                'aps': {
                    'alert': 'You have been tagged in a photo from ' + album_name,
                    'sound': 'default'
                    }
                }
            }
    send_message_or_log_errors(rq)


def broadcast_user_glance_score_update(user_id, user_glance_score):
    payload = {
            'type': 'user_glance_score_update',
            'user_glance_score': user_glance_score
        }

    rq = {
            'user_ids': [str(user_id)],
            'gcm': {
                'data': {
                    'd': json.dumps(payload)
                    }
                },
            'apns': {
                'aps': {},
                'd': payload
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


def broadcast_photo_in_public_feed(user_ids, media_type, photo_id):
    payload = {
            'type': 'photo_in_public_feed',
            'media_type': media_type,
            'photo_id': photo_id
        }

    alert_text = u"\u2B50\u2B50 Your " + media_type + u" has made it into the public feed! 250 points! Keep glancing \u2B50\u2B50"
    rq = {
            'user_ids': [str(id) for id in user_ids],
            'gcm': {
                'data': {
                    'd': json.dumps(payload)
                    }
                },
            'apns': {
                'aps': {
                    'alert': alert_text,
                    'sound': 'push.mp3',
                    'badge': 1
                    },
                'd': payload
                }
            }
    send_message_or_log_errors(rq)
