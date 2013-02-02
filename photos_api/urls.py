from django.conf.urls import patterns, url, include

from rest_framework.urlpatterns import format_suffix_patterns

from photos_api import views

urlpatterns = patterns('',
    url(r'^$', views.api_root),
    url(r'^albums/$', views.Albums.as_view(), name='album-list'),
    url(r'^albums/(?P<pk>\d+)/$', views.AlbumDetail.as_view(), name='album-detail'),
    url(r'^users/$', views.UserList.as_view(), name='user-list'),
    url(r'^users/(?P<pk>\d+)/$', views.UserDetail.as_view(), name='user-detail'),
)

# Format suffixes
urlpatterns = format_suffix_patterns(urlpatterns, allowed=['json', 'api'])

# Default login/logout views
urlpatterns += patterns('',
    url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework'))
)