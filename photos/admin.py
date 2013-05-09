from django.contrib import admin
from django.utils.html import format_html

from photos.models import Album, Photo

class PhotoAdminInline(admin.TabularInline):
    model = Photo

    fields = ('bucket', 'date_created', 'author', 'album', 'photo_thumbnail', 'width', 'height')
    readonly_fields = ('bucket', 'date_created', 'author', 'album', 'photo_thumbnail', 'width', 'height')

    ordering = ['date_created', 'photo_id']

    extra = 0
    max_num = 0

    def photo_thumbnail(self, instance):
        return format_html(u'<img src="{0}" />', instance.get_photo_url_no_ext() + '_thumb75.jpg')

class AlbumAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'date_created', 'creator')
    list_display_links = list_display

    readonly_fields = ('creator', 'revision_number', 'last_updated', 'date_created')

    filter_horizontal = ('members',)

    inlines = [PhotoAdminInline]

class PhotoAdmin(admin.ModelAdmin):
    list_display = ('photo_id', 'album', 'date_created', 'author',)
    list_display_links = list_display

    readonly_fields = ('photo_id', 'bucket', 'date_created', 'author', 'album', 'width', 'height', 'photo_thumbnail',)

    def photo_thumbnail(self, instance):
        return format_html(u'<img src="{0}" />', instance.get_photo_url_no_ext() + '_thumb75.jpg')

admin.site.register(Photo, PhotoAdmin)
admin.site.register(Album, AlbumAdmin)
