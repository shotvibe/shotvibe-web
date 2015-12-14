from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework.exceptions import AuthenticationFailed
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from photos_api.permissions import IsAllowedPrivateAPI
from photos_api.serializers import PhotoUploadInitSerializer, PhotoServerRegisterSerializer
from phone_auth.authentication import TokenAuthentication
from phone_auth.models import User
from photos.models import Album, PendingPhoto, Photo, Video
from photos import photo_operations
from photos_api.private_serializers import VideoObjectSerializer


@api_view(['POST'])
@permission_classes((IsAllowedPrivateAPI, ))
def photo_upload_init(request, photo_id):
    serializer = PhotoUploadInitSerializer(data=request.DATA)

    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        user, token = TokenAuthentication().authenticate_credentials(serializer.object['user_auth_token'])
    except AuthenticationFailed as e:
        return Response({
            'success': False,
            'error': 'user_auth_failed',
            'detail': e.detail
            })

    try:
        photo = PendingPhoto.objects.get(pk=photo_id)
    except PendingPhoto.DoesNotExist:
        photo = get_object_or_404(Photo, pk=photo_id)

    if photo.author != user:
        return Response({
            'success': False,
            'error': 'user_not_permitted'
            })

    return Response({
        'success': True,
        'storage_id': photo.storage_id,
        'uploaded': True if isinstance(photo, Photo) else photo.is_file_uploaded()
        })


@api_view(['PUT'])
@permission_classes((IsAllowedPrivateAPI, ))
def photo_file_uploaded(request, photo_id):
    pending_photo = get_object_or_404(PendingPhoto, pk=photo_id)

    now = timezone.now()
    pending_photo.set_uploaded(now)

    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['PUT'])
@permission_classes((IsAllowedPrivateAPI, ))
def photo_processing_done(request, storage_id):
    pending_photo = get_object_or_404(PendingPhoto, storage_id=storage_id)

    now = timezone.now()
    pending_photo.set_processing_done(now)

    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['PUT'])
@permission_classes((IsAllowedPrivateAPI, ))
def video_object(request, storage_id):
    serializer = VideoObjectSerializer(data=request.DATA)

    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    author_id = serializer.object['author_id']
    client_upload_id = serializer.object['client_upload_id']
    album_id = serializer.object['album_id']
    status_ = serializer.object['status']

    try:
        author = User.objects.get(pk=author_id)
    except User.DoesNotExist:
        return Response('Invalid user id: ' + str(author_id), status=status.HTTP_400_BAD_REQUEST)

    try:
        album = Album.objects.get(pk=album_id)
    except Album.DoesNotExist:
        return Response('Invalid album id: ' + str(album_id), status=status.HTTP_400_BAD_REQUEST)

    # TODO Verify that the author is allowed to add a video into album

    now = timezone.now()

    if status_ == 'processing':
        Video.objects.set_processing(client_upload_id, storage_id, author, album, now)
    elif status_ == 'ready':
        duration = serializer.object.get('duration')
        if duration is None:
            return Response('Missing required field "duration"', status=status.HTTP_400_BAD_REQUEST)
        Video.objects.set_ready(client_upload_id, storage_id, author, album, duration, now)
    elif status_ == 'invalid':
        Video.objects.set_invalid(client_upload_id, storage_id, author, album, now)
    else:
        raise RuntimeError('Unknown status: ' + status_)

    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['POST'])
@permission_classes((IsAllowedPrivateAPI, ))
def photo_server_register(request):
    serializer = PhotoServerRegisterSerializer(data=request.DATA)

    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    now = timezone.now()
    photo_operations.register_photo_server(
            serializer.object['update_url'],
            serializer.object['subdomain'],
            serializer.object['auth_key'],
            now)

    return Response(status=status.HTTP_204_NO_CONTENT)
