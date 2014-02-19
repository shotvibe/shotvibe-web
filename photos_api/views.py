import random
import tempfile

import json
from boto.s3.connection import S3Connection
from boto.s3.key import Key

from django.core.files import File
from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from django.contrib import auth
from django.db.models import Q
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt

#from django.http import HttpResponseNotModified
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from phone_auth.signals import user_avatar_changed
from photos_api.permissions import IsUserInAlbum, UserDetailsPagePermission, \
    IsSameUserOrStaff
from photos_api.parsers import PhotoUploadParser
from photos_api import device_push, is_phone_number_mobile
from phone_auth.models import AnonymousPhoneNumber, random_default_avatar_file_data, User, PhoneContact, PhoneNumber
from photos_api.signals import photos_added_to_album, member_leave_album

from rest_framework import generics, serializers, mixins
from rest_framework.decorators import api_view, permission_classes
from rest_framework.generics import GenericAPIView
from rest_framework.reverse import reverse
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework import status
from rest_framework import views

import requests

import phonenumbers

from photos.image_uploads import process_file_upload
from photos.models import Album, PendingPhoto, AlbumMember, Photo
from photos_api.serializers import AlbumNameSerializer, AlbumSerializer, \
    UserSerializer, AlbumUpdateSerializer, AlbumAddSerializer, \
    QueryPhonesRequestSerializer, DeletePhotosSerializer, \
    AlbumMemberNameSerializer, AlbumMemberSerializer, AlbumViewSerializer, \
    AlbumMembersSerializer
from photos_api.check_modified import supports_last_modified, supports_etag

from photos import photo_operations


@api_view(['GET'])
def api_root(request, format=None):
    """
    The entry endpoint of our API.
    """
    response_data = {
        'all_albums': reverse('album-list', request=request),
        'all_users': reverse('user-list', request=request),
        'upload_photos_request': reverse('photos-upload-request', request=request),
    }
    return Response(response_data)


class AlbumList(generics.ListAPIView):
    """
    The list of all albums in the database, of all users.
    """
    permission_classes = (IsAdminUser,)
    model = Album
    serializer_class = AlbumNameSerializer


def parse_phone_number(phone_number, default_country):
    try:
        number = phonenumbers.parse(phone_number, default_country)
    except phonenumbers.phonenumberutil.NumberParseException:
        return None

    if not phonenumbers.is_possible_number(number):
        return None

    return phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.E164)


@supports_etag
class AlbumDetail(generics.RetrieveAPIView):
    model = Album
    serializer_class = AlbumSerializer
    permission_classes = (IsUserInAlbum,)

    def initial(self, request, pk, *args, **kwargs):
        self.album = get_object_or_404(Album, pk=pk)

        if request.user.is_staff:
            self.is_staff = True
        elif request.user.is_authenticated():
            self.is_staff = False

        return super(AlbumDetail, self).initial(request, pk, *args, **kwargs)

    def get_object(self):
        if self.is_staff:
            return self.album
        else:
            return AlbumMember.objects\
                .get_user_memberships(self.request.user.id)\
                .filter(album=self.album)\
                .get()

    def get_serializer_class(self):
        if self.is_staff:
            return AlbumSerializer
        else:
            return AlbumMemberSerializer

    def get_etag(self, request, pk):
        return self.album.get_etag()

    def post(self, request, pk):
        serializer = AlbumUpdateSerializer(data=request.DATA)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        if serializer.object.add_photos:
            now = timezone.now()

            photo_ids = serializer.object.add_photos

            try:
                photo_operations.add_pending_photos_to_album(photo_ids, self.album.id, now)
            except photo_operations.PhotoNotUploadedAddPhotoException:
                return Response(u"Trying to add a Photo that has not yet been uploaded", status=status.HTTP_400_BAD_REQUEST)
            except photo_operations.InvalidPhotoIdAddPhotoException:
                return Response(u"Trying to add a Photo with an invalid photo_id", status=status.HTTP_400_BAD_REQUEST)

            photos_added_to_album.send(sender=self,
                                       photos=photo_ids,
                                       by_user=request.user,
                                       to_album=self.album)

        self.album.add_members(request.user, member_identifiers=serializer.object.add_members)

        responseSerializer = (self.get_serializer_class())(self.get_object(), context={'request': request})
        return Response(responseSerializer.data)


class AlbumMembersView(generics.CreateAPIView):
    model = Album
    permission_classes = (IsUserInAlbum,)
    serializer_class = AlbumMembersSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.DATA, files=request.FILES)

        if serializer.is_valid():
            album = Album.objects.get(pk=kwargs.get('pk'))
            result = album.add_members(request.user,
                                       serializer.object['members'])

            return Response(result, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LeaveAlbum(generics.DestroyAPIView):
    model = AlbumMember
    permission_classes = (IsAuthenticated, IsUserInAlbum)

    def post(self, request, *args, **kwargs):
        album = self.get_object().album
        response = self.delete(request, *args, **kwargs)

        member_leave_album.send(sender=self, user=request.user, album=album)

        return response

    def get_object(self, queryset=None):

        if queryset is None:
            queryset = self.get_queryset()

        # pk from URL points to the album, not AlbumMember
        album_pk = self.kwargs.get(self.pk_url_kwarg, None)
        if album_pk is None:
            raise AttributeError("Missing Album pk")

        try:
            obj = queryset.get(user=self.request.user, album__pk=album_pk)
        except self.model.DoesNotExist:
            # This should never happen since we already checked if this records exists by checking permissions
            raise Http404(_(u"Album not found"))
        return obj


class ViewAlbum(GenericAPIView):
    permission_classes = (IsAuthenticated, IsUserInAlbum)
    serializer_class = AlbumViewSerializer

    def post(self, request, *args, **kwargs):
        serializer = AlbumViewSerializer(data=request.DATA)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        timestamp = serializer.object
        if timestamp.tzinfo is None:
            return Response(u"Missing timezone", status=status.HTTP_400_BAD_REQUEST)

        album_pk = self.kwargs.get(self.pk_url_kwarg, None)
        if album_pk is None:
            raise AttributeError("Missing Album pk")

        obj = AlbumMember.objects.get(user=self.request.user, album__pk=album_pk)
        obj.update_last_access(timestamp)

        return Response(status=status.HTTP_204_NO_CONTENT)


class UserList(generics.ListCreateAPIView):
    """
    API endpoint that represents a list of users.
    """
    model = auth.get_user_model()
    serializer_class = UserSerializer


class UserDetail(generics.RetrieveUpdateAPIView):
    """
    API endpoint that represents a single user.
    """
    model = auth.get_user_model()
    serializer_class = UserSerializer
    permission_classes = (UserDetailsPagePermission,)

    # These attributes can be changed with PUT or PATCH request
    __allowed_attributes_to_change = ['nickname']

    def __check_update_attr_permissions(self, request):
        """Ensure that only allowed attributes can be changed"""
        for key, value in request.DATA.iteritems():
            if key not in self.__allowed_attributes_to_change:
                raise PermissionDenied("You are not allowed to "
                                       "change '{0}'".format(key))

    def get_queryset(self):
        """For PUT and PATCH requests limit queryset to only user
        who makes request"""

        if self.request.method in ['PUT', 'PATCH']:
            return self.model.objects.filter(pk=self.request.user.pk)

        return super(UserDetail, self).get_queryset()

    def put(self, request, *args, **kwargs):
        """PUT handler"""
        self.__check_update_attr_permissions(request)
        return super(UserDetail, self).put(request, *args, **kwargs)

    def patch(self, request, *args, **kwargs):
        """PATCH handler"""
        self.check_permissions(request)
        self.__check_update_attr_permissions(request)
        return super(UserDetail, self).patch(request, *args, **kwargs)


class UserAvatarDetail(views.APIView):
    """View that handles avatar uploads"""
    permission_classes = (IsAuthenticated, IsSameUserOrStaff)

    parser_classes = (PhotoUploadParser,)

    def process_upload_request(self, request, uploaded_chunks):
        """Uploads user avatar to the randomly picked location
        where we host user avatars and returns Response"""

        avatar_image_filename = settings.AVATAR_FILENAME_FORMAT_STRING.format(
            user_id=request.user.id,
            timestamp=timezone.now().strftime("%s")
        )
        avatar_location_format_str = random.choice(settings.AVATAR_BUCKETS)
        storage, bucket_name, filename = avatar_location_format_str.split(":")

        # Write uploaded data to temporary file
        # File will be delete once handler is closed
        temp_file = tempfile.TemporaryFile()
        for chunk in uploaded_chunks:
            temp_file.write(chunk)
        temp_file.seek(0)

        if storage == "s3":
            # Upload to S3
            try:
                conn = S3Connection(settings.AWS_ACCESS_KEY,
                                    settings.AWS_SECRET_ACCESS_KEY)
                bucket = conn.get_bucket(bucket_name)
                key = Key(bucket, avatar_image_filename)
                key.metadata = {'Content-Type': 'image/jpeg'}
                key.set_contents_from_file(temp_file)
                # Otherwise it's not accessible
                key.make_public()
                key.close(fast=True)
                temp_file.close()
            except:
                temp_file.close()
                raise
        else:
            temp_file.close()
            raise ValueError("Failed to upload avatar. "
                             "Unknown storage '{0}'.".format(storage))

        request.user.avatar_file = avatar_location_format_str.format(
            filename=avatar_image_filename)
        request.user.save()

        user_avatar_changed.send(sender=self, user=request.user)

        return Response()

    def post(self, request, *args, **kwargs):
        return self.process_upload_request(request,
                                           request.FILES['photo'].chunks())

    def put(self, request, *args, **kwargs):
        return self.process_upload_request(request,
                                           request.DATA.chunks())


@supports_last_modified
class Albums(generics.ListAPIView):
    """
    This Resource supports the "If-Modified-Since" HTTP header.

    Clients should remember the value returned in the "Date" HTTP header, and
    use this as the value of "If-Modified-Since" for future requests.

    If there have been no updates to the resource, the server will return an
    empty response body, and a status code of: 304 Not Modified
    """
    permission_classes = (IsAuthenticated,)

    def initial(self, request, *args, **kwargs):
        if request.user.is_staff:
            self.is_staff = True
            self.albums = Album.objects.all()
        elif request.user.is_authenticated():
            self.is_staff = False
            self.albums = AlbumMember.objects.get_user_memberships(self.request.user.id)

        return super(Albums, self).initial(request, *args, **kwargs)

    def last_modified(self, request):
        if not self.albums:
            return None

        if self.is_staff:
            return max([a.last_updated for a in self.albums])
        else:
            return max([m.album.last_updated for m in self.albums])

    def get_serializer_class(self):
        if self.is_staff:
            return AlbumNameSerializer
        else:
            return AlbumMemberNameSerializer

    def get_queryset(self):
        return self.albums

    def post(self, request):
        serializer = AlbumAddSerializer(data=request.DATA)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        album = Album.objects.create_album(self.request.user, serializer.object.album_name)
        album.add_members(request.user, member_identifiers=serializer.object.members)

        responseSerializer = AlbumSerializer(album, context={'request': request})
        return Response(responseSerializer.data)


class DeletePhotosView(mixins.DestroyModelMixin, generics.MultipleObjectAPIView):
    model = Photo
    serializer_class = DeletePhotosSerializer

    def post(self, request, *args, **kwargs):
        self.object_list = self.get_queryset()
        for photo in self.object_list:

            if photo.author == self.request.user:
                album = photo.album or None
                photo.delete()

                # Save album revision, because we deleted photo from it.
                album.save_revision(timezone.now())

        return Response(status=status.HTTP_204_NO_CONTENT)

    def get_queryset(self):
        serializer = self.get_serializer(data=json.loads(self.request.body))
        if serializer.is_valid():
            queryset = self.model._default_manager.filter(
                photo_id__in=serializer.data.get('photos', []))
            return queryset
        else:
            return self.model._default_manager.none()


@api_view(['POST'])
@permission_classes((IsAuthenticated, ))
def photos_upload_request(request, format=None):
    """
    Use the GET parameter `num_photos` to specify how many photos you would
    like to upload
    """
    num_photos = int(request.GET.get('num_photos', 1))

    response_data = []
    for i in xrange(num_photos):
        pending_photo = Photo.objects.upload_request(author=request.user)
        response_data.append({
            'photo_id': pending_photo.photo_id,
            'upload_url': reverse('photo-upload', [pending_photo.photo_id], request=request)
            })

    return Response(response_data)


class PhotoUpload(views.APIView):
    permission_classes = (IsAuthenticated,)

    parser_classes = (PhotoUploadParser,)

    @transaction.non_atomic_requests
    @csrf_exempt
    def dispatch(self, *args, **kwargs):
        return super(PhotoUpload, self).dispatch(*args, **kwargs)

    def process_upload_request(self, request, photo_id, uploaded_chunks):
        pending_photo = get_object_or_404(PendingPhoto, pk=photo_id)
        if pending_photo.author != request.user:
            return Response(status=403)

        if settings.USING_LOCAL_PHOTOS:
            process_file_upload(pending_photo, uploaded_chunks)
        else:
            # Forward request to photo upload server
            r = requests.put(settings.PHOTO_UPLOAD_SERVER_FORWARD_URL.format(pending_photo.photo_id),
                    headers = { 'Authorization': 'Token ' + request.auth.key },
                    data = uploaded_chunks)
            r.raise_for_status()

        return Response()

    def post(self, request, photo_id, format=None):
        return self.process_upload_request(request, photo_id,
                                           request.FILES['photo'].chunks())

    def put(self, request, photo_id, format=None):
        return self.process_upload_request(request, photo_id,
                                           request.DATA.chunks())


class QueryPhoneNumbers(GenericAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = QueryPhonesRequestSerializer

    def __process_requested_item(self, user, country_code, existing_contacts,
                                 phone_number, nickname):

        try:
            number = phonenumbers.parse(phone_number, country_code)
        except phonenumbers.phonenumberutil.NumberParseException as e:
            return {'phone_type': 'invalid'}

        if not phonenumbers.is_possible_number(number):
            return {'phone_type': 'invalid'}

        phone_number_str = phonenumbers.format_number(
            number,
            phonenumbers.PhoneNumberFormat.E164
        )

        existing_phone_contact = existing_contacts.get(phone_number_str)
        if existing_phone_contact:
            phone_contact = existing_phone_contact
            apn = phone_contact.anonymous_phone_number
        else:
            try:
                apn = AnonymousPhoneNumber.objects.get(phone_number=phone_number_str)
            except AnonymousPhoneNumber.DoesNotExist:
                is_mobile = is_phone_number_mobile(number)
                apn = AnonymousPhoneNumber.objects.create(
                    phone_number=phone_number_str,
                    date_created=timezone.now(),
                    avatar_file=random_default_avatar_file_data(),
                    is_mobile=is_mobile,
                    is_mobile_queried=timezone.now()
                )

            try:
                phone_contact = apn.phonecontact_set.get(created_by_user=user)
            except PhoneContact.DoesNotExist:
                try:
                    owner_user = PhoneNumber.objects.only('user').\
                        get(phone_number=phone_number_str).user
                except PhoneNumber.DoesNotExist:
                    owner_user = None
                phone_contact = PhoneContact.objects.create(
                    anonymous_phone_number=apn,
                    user=owner_user,
                    created_by_user=user,
                    date_created=timezone.now(),
                    contact_nickname=nickname
                )

        user = phone_contact.user
        if user:
            if user.get_invite_status() == User.STATUS_JOINED:
                user_id = user.id
            else:
                user_id = None
        else:
            user_id = None

        if phone_contact.user:
            avatar_url = phone_contact.user.get_avatar_url()
        else:
            avatar_url = apn.get_avatar_url()

        data = {}
        data['phone_type'] = 'mobile' if apn.is_mobile else 'landline'
        data['avatar_url'] = avatar_url
        data['user_id'] = user_id
        data['phone_number'] = apn.phone_number
        return data

    def post(self, request, *args, **kwargs):
        data = json.loads(str(request.body))
        serializer = self.get_serializer(data=data, files=request.FILES)
        if not serializer.is_valid():
            return Response(serializer.errors,
                            status=status.HTTP_400_BAD_REQUEST)

        default_country = serializer.data.get('default_country')
        phone_numbers = serializer.data.get('phone_numbers')

        q = Q()
        for pn in phone_numbers:
            try:
                number = phonenumbers.parse(pn['phone_number'], default_country)
            except phonenumbers.phonenumberutil.NumberParseException as e:
                continue

            phone_number_str = phonenumbers.format_number(
                    number,
                    phonenumbers.PhoneNumberFormat.E164)

            q = q | Q(anonymous_phone_number__phone_number=phone_number_str)

        existing_contacts = {}
        for existing_contact in PhoneContact.objects.filter(q, created_by_user=request.user):
            existing_contacts[existing_contact.anonymous_phone_number.phone_number] = existing_contact

        response_items = []
        for pn in phone_numbers:
            item = self.__process_requested_item(request.user,
                                                 default_country,
                                                 existing_contacts,
                                                 pn['phone_number'],
                                                 pn['contact_nickname'])
            response_items.append(item)

        # return Response(json.dumps(response_items))
        return Response({'phone_number_details': response_items})
