from django.conf.urls import patterns, url

from phone_auth import views

urlpatterns = patterns('',
    url(r'^authorize_phone_number/', views.AuthorizePhoneNumber.as_view()),
    url(r'^confirm_sms_code/(?P<confirmation_key>[\w]+)/$', views.ConfirmSMSCode.as_view()),
    url(r'^logout/', views.logout),
    url(r'^delete_account/', views.delete_account),
    url(r'^country_lookup/$', views.country_lookup),
    url(r'^aws_token/$', views.aws_token),
)
