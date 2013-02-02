from django.contrib import admin
from models import Album, Photo

class PhotoAdminInline(admin.TabularInline):
    model = Photo

class AlbumAdmin(admin.ModelAdmin):
    inlines = [PhotoAdminInline]

admin.site.register(Photo)
admin.site.register(Album, AlbumAdmin)
