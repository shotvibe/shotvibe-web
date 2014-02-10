from django.shortcuts import get_object_or_404

from rest_framework.exceptions import AuthenticationFailed
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from photos_api.permissions import IsAllowedPrivateAPI
from photos_api.serializers import PhotoUploadInitSerializer
from phone_auth.authentication import TokenAuthentication
from photos.models import PendingPhoto

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
        'storage_id': pending_photo.storage_id
        })
