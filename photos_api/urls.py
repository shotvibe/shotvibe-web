from django.conf.urls import patterns, url, include

from rest_framework.urlpatterns import format_suffix_patterns

from photos_api import views
from photos_api import private_urls
from photos_api import device_push

urlpatterns = patterns('',
    url(r'^$', views.api_root),
    url(r'^auth/', include('phone_auth.urls')),
    url(r'^gcm/devices/(?P<device_id>[\w-]+)/$', device_push.GcmDevice.as_view(), name='gcm-device'), # Deprecated
    url(r'^register_device_push/$', device_push.register_device_push, name='register-device-push'),
    url(r'^albums/$', views.Albums.as_view(), name='album-list'),
    url(r'^albums/(?P<pk>\d+)/$', views.AlbumDetail.as_view(), name='album-detail'),
    url(r'^albums/(?P<pk>\d+)/name/$', views.AlbumNameView.as_view(), name='album-name'),
    url(r'^albums/(?P<pk>\d+)/members/$', views.AlbumMembersView.as_view(), name='album-members'),
    url(r'^albums/(?P<pk>\d+)/members/(?P<user_id>\d+)/phone_number/$', views.AlbumMemberPhoneNumberView.as_view(), name='album-member-phonenumber'),
    url(r'^albums/(?P<pk>\d+)/leave/$', views.LeaveAlbum.as_view(), name='album-leave'),
    url(r'^albums/(?P<pk>\d+)/members/(?P<user_id>\d+)/$', views.AlbumMemberUser.as_view(), name='album-member-user'),
    url(r'^albums/(?P<pk>\d+)/view/$', views.ViewAlbum.as_view(), name='album-view'),
    url(r'^albums/public/$', views.PublicAlbum.as_view(), name='public-album'),
    url(r'^users/$', views.UserList.as_view(), name='user-list'),
    url(r'^competition/$', views.CompetitionUserList.as_view(), name='competition-list'),
    url(r'^users/(?P<pk>\d+)/$', views.UserDetail.as_view(), name='user-detail'),
    url(r'^users/(?P<pk>\d+)/glance_score/$', views.UserGlanceScore.as_view(), name='user-glance-score'),
    url(r'^users/(?P<pk>\d+)/avatar/$', views.UserAvatarDetail.as_view(), name='user-avatar'),
    url(r'^photos/delete/$', views.DeletePhotosView.as_view(), name='photos-delete'),
    url(r'^photos/upload_request/$', views.photos_upload_request, name='photos-upload-request'),
    url(r'^photos/upload/(?P<photo_id>[\w-]+)/$', views.PhotoUpload.as_view(), name='photo-upload'),
    url(r'^photos/(?P<photo_id>[\w-]+)/glance/$', views.PhotoGlanceView.as_view(), name='photo-glance'),
    url(r'^photos/(?P<photo_id>[\w-]+)/comments/(?P<author_id>\d+)/(?P<client_msg_id>\d+)/$', views.PhotoCommentView.as_view(), name='photo-comment'),
    url(r'^photos/(?P<photo_id>[\w-]+)/user_tags/(?P<tagged_user_id>\d+)/$', views.PhotoUserTagView.as_view(), name='photo-user-tag'),
    url(r'^photos/(?P<photo_id>[\w-]+)/glance_scores/(?P<author_id>\d+)/', views.PhotoGlanceScoreView.as_view(), name='photo-glance-score'),
    url(r'^query_phone_numbers/$', views.QueryPhoneNumbers.as_view(),
    # url(r'^upload_youtube/$', views.UploadYouTube.as_view(),
        name='query-phone-numbers')
)

# Format suffixes
urlpatterns = format_suffix_patterns(urlpatterns, allowed=['json', 'api'])

# Default login/logout views
urlpatterns += patterns('',
    url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework'))
)

urlpatterns += patterns('',
    url(r'^private/', include(private_urls))
)
