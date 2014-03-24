from django import forms
from django.contrib import admin
from django.db import models
from django.utils.html import format_html

from photos.models import Album, AlbumMember, Photo, PendingPhoto
from photos.models import PhotoServer

class PhotoAdminInline(admin.TabularInline):
    model = Photo

    fields = ('photo_id', 'storage_id', 'subdomain', 'date_created', 'author', 'album', 'photo_thumbnail')
    readonly_fields = ('storage_id', 'subdomain', 'date_created', 'author', 'album', 'photo_thumbnail')

    ordering = ['album_index']

    # This inline suffers from the following Django bug:
    # https://code.djangoproject.com/ticket/19888
    #
    # The bug is that the primary key ('photo_id') must be in 'fields' and must
    # not be in 'readonly_fields'
    #
    # But we don't want the user to be able to actually change the value, so
    # the ugly (and also sadly insecure) workaround here is to use an HTML form
    # 'readonly' attribute to prevent editing
    formfield_overrides = {
            models.CharField: { 'widget': forms.TextInput(attrs={'readonly':'readonly'}) }
            }

    extra = 0
    max_num = 0

    def photo_thumbnail(self, instance):
        return format_html(u'<img src="{0}" />', instance.get_photo_url_no_ext() + '_thumb75.jpg')

class AlbumMemberInline(admin.TabularInline):
    model = AlbumMember

    fields = ('user', 'added_by_user', 'datetime_added')
    readonly_fields = ('user', 'added_by_user', 'datetime_added')

    ordering = ('datetime_added',)

    can_delete = False

    extra = 0
    max_num = 0

class AlbumAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'date_created', 'creator')
    list_display_links = list_display

    readonly_fields = ('creator', 'revision_number', 'last_updated', 'date_created')

    inlines = [AlbumMemberInline, PhotoAdminInline]

class PhotoAdmin(admin.ModelAdmin):
    list_display = ('photo_id', 'album', 'date_created', 'author',)
    list_display_links = list_display

    readonly_fields = ('photo_id', 'storage_id', 'subdomain', 'date_created', 'author', 'album', 'photo_thumbnail',)

    def photo_thumbnail(self, instance):
        return format_html(u'<img src="{0}" />', instance.get_photo_url_no_ext() + '_thumb75.jpg')

class PendingPhotoAdmin(admin.ModelAdmin):
    pass

class PhotoServerAdmin(admin.ModelAdmin):
    pass

admin.site.register(Photo, PhotoAdmin)
admin.site.register(PendingPhoto, PendingPhotoAdmin)
admin.site.register(Album, AlbumAdmin)
admin.site.register(PhotoServer, PhotoServerAdmin)
