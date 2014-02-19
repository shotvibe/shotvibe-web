from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework.exceptions import AuthenticationFailed
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from photos_api.permissions import IsAllowedPrivateAPI
from photos_api.serializers import PhotoUploadInitSerializer, PhotoServerRegisterSerializer
from phone_auth.authentication import TokenAuthentication
from photos.models import PendingPhoto
from photos import photo_operations

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

    pending_photo = get_object_or_404(PendingPhoto, pk=photo_id)

    if pending_photo.author != user:
        return Response({
            'success': False,
            'error': 'user_not_permitted'
            })

    return Response({
        'success': True,
        'storage_id': pending_photo.storage_id,
        'uploaded': pending_photo.is_file_uploaded()
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
