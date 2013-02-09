from django.conf.urls import patterns, include, url
from django.contrib import admin

import frontend.urls

admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'shotvibe_site.views.home', name='home'),
    # url(r'^shotvibe_site/', include('shotvibe_site.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    url(r'^', include(frontend.urls)),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),
)
