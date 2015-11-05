from django import forms
from django.contrib import admin
from django.db import models
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from phone_auth.models import PhoneNumberLinkCode
from photos.models import Album, AlbumMember, Photo, PendingPhoto, PhotoComment, PhotoGlance, PhotoGlanceScoreDelta
from photos.models import PhotoServer

class PhotoAdminInline(admin.TabularInline):
    model = Photo

    fields = ('photo_id', 'storage_id', 'subdomain', 'date_created', 'author', 'album', 'photo_thumbnail', 'comments', 'photo_glance_score', 'photo_glance_votes')
    readonly_fields = ('subdomain', 'date_created', 'author', 'album', 'photo_thumbnail', 'comments', 'photo_glance_score', 'photo_glance_votes')

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

    def comments(self, obj):
        comments = obj.get_comments()
        if not comments:
            return None

        html = u'<ul>'
        for comment in comments:
            html += format_html(u'<li>"{0}" <a href="{1}">{2}</a></li>',
                    comment.comment_text,
                    u'../../../{0}/{1}/{2}/'.format(comment.author._meta.app_label, comment.author._meta.module_name, comment.author.id),
                    comment.author)
        html += u'</ul>'
        return mark_safe(html)

    def photo_glance_votes(self, obj):
        votes = PhotoGlanceScoreDelta.objects.filter(photo=obj).order_by('date_created')
        if not votes:
            return None

        html = u'<ul>'
        for vote in votes:
            html += format_html(u'<li><a href="{0}">{1}</a>: {2}</li>',
                    u'../../../{0}/{1}/{2}/'.format(vote.author._meta.app_label, vote.author._meta.module_name, vote.author.id),
                    vote.author,
                    vote.score_delta)
        html += u'</ul>'
        return mark_safe(html)


class AlbumMemberInline(admin.TabularInline):
    model = AlbumMember

    fields = ('avatar', 'user_link', 'first_phone_number', 'first_phone_number_verified', 'invite_link_visited', 'datetime_added', 'added_by_user_link', 'last_access')
    readonly_fields = fields

    ordering = ('datetime_added',)

    can_delete = False

    extra = 0
    max_num = 0

    def user_link(self, obj):
        return format_html(u'<a href="{0}">{1}</a>',
                u'../../../{0}/{1}/{2}/'.format(obj.user._meta.app_label, obj.user._meta.module_name, obj.user.id),
                obj.user)
    user_link.short_description = 'User'
    user_link.admin_order_field = 'user'
    user_link.allow_tags = True

    def added_by_user_link(self, obj):
        return format_html(u'<a href="{0}">{1}</a>',
                u'../../../{0}/{1}/{2}/'.format(obj.added_by_user._meta.app_label, obj.added_by_user._meta.module_name, obj.added_by_user.id),
                obj.added_by_user)
    added_by_user_link.short_description = 'Added by user'
    added_by_user_link.admin_order_field = 'added_by_user'
    added_by_user_link.allow_tags = True

    def first_phone_number(self, instance):
        return instance.user.phonenumber_set.all()[:1].get()

    def first_phone_number_verified(self, instance):
        phone_number = instance.user.phonenumber_set.first()
        if phone_number:
            return phone_number.verified
        else:
            return None
    first_phone_number_verified.short_description = 'Verified'
    first_phone_number_verified.boolean = True

    def avatar(self, instance):
        return format_html(u'<img src="{0}" width="24" height="24">', instance.user.get_avatar_url())

    def invite_link_visited(self, instance):
        try:
            link_code = PhoneNumberLinkCode.objects.get(phone_number=self.first_phone_number(instance))
            return link_code.was_visited
        except PhoneNumberLinkCode.DoesNotExist:
            return None
    invite_link_visited.boolean = True


class AlbumAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'date_created', 'creator')
    list_display_links = list_display

    readonly_fields = ('creator', 'revision_number', 'last_updated', 'date_created')

    inlines = [AlbumMemberInline, PhotoAdminInline]

class PhotoAdmin(admin.ModelAdmin):
    list_display = ('photo_icon', 'photo_id', 'album_link', 'date_created', 'author_link',)
    list_display_links = list_display

    readonly_fields = ('photo_id', 'storage_id', 'subdomain', 'date_created', 'author', 'album', 'photo_thumbnail',)

    ordering = ('-date_created', '-album_index')

    def photo_icon(self, obj):
        return format_html(u'<img src="{0}" width="35" height="35">', obj.get_photo_url_no_ext() + '_crop140.jpg')
    photo_icon.short_description = 'Photo'

    def album_link(self, obj):
        return format_html(u'<a href="{0}">{1}</a>',
                u'../../{0}/{1}/{2}/'.format(obj.album._meta.app_label, obj.album._meta.module_name, obj.album.id),
                obj.album.name)
    album_link.short_description = 'Album'
    album_link.admin_order_field = 'album'

    def author_link(self, obj):
        return format_html(u'<a href="{0}">{1}</a>',
                u'../../{0}/{1}/{2}/'.format(obj.author._meta.app_label, obj.author._meta.module_name, obj.author.id),
                obj.author)
    author_link.short_description = 'Author'
    author_link.admin_order_field = 'author'

    def photo_thumbnail(self, instance):
        return format_html(u'<img src="{0}" />', instance.get_photo_url_no_ext() + '_thumb75.jpg')

class PendingPhotoAdmin(admin.ModelAdmin):
    pass


class PhotoCommentAdmin(admin.ModelAdmin):
    list_display = ('photo_icon', 'album_link', 'comment_text', 'date_created', 'author_link')
    list_display_links = list_display

    ordering = ('-date_created',)

    def photo_icon(self, obj):
        return format_html(u'<img src="{0}" width="35" height="35">', obj.photo.get_photo_url_no_ext() + '_crop140.jpg')
    photo_icon.short_description = 'Photo'
    photo_icon.admin_order_field = 'photo'

    def album_link(self, obj):
        return format_html(u'<a href="{0}">{1}</a>',
                u'../../{0}/{1}/{2}/'.format(obj.photo.album._meta.app_label, obj.photo.album._meta.module_name, obj.photo.album.id),
                obj.photo.album.name)
    album_link.short_description = 'Album'
    album_link.admin_order_field = 'album'

    def comment_text(self, obj):
        return obj.comment_text

    def author_link(self, obj):
        return format_html(u'<a href="{0}">{1}</a>',
                u'../../{0}/{1}/{2}/'.format(obj.author._meta.app_label, obj.author._meta.module_name, obj.author.id),
                obj.author)
    author_link.short_description = 'Author'
    author_link.admin_order_field = 'author'


class PhotoGlanceAdmin(admin.ModelAdmin):
    list_display = ('photo_icon', 'album_link', 'emoticon_icon', 'date_created', 'author_link')
    list_display_links = list_display

    ordering = ('-date_created',)

    def photo_icon(self, obj):
        return format_html(u'<img src="{0}" width="35" height="35">', obj.photo.get_photo_url_no_ext() + '_crop140.jpg')
    photo_icon.short_description = 'Photo'
    photo_icon.admin_order_field = 'photo'

    def album_link(self, obj):
        return format_html(u'<a href="{0}">{1}</a>',
                u'../../{0}/{1}/{2}/'.format(obj.photo.album._meta.app_label, obj.photo.album._meta.module_name, obj.photo.album.id),
                obj.photo.album.name)
    album_link.short_description = 'Album'
    album_link.admin_order_field = 'album'

    def emoticon_icon(self, obj):
        return format_html(u'<img src="{0}">', PhotoGlance.GLANCE_EMOTICONS_BASE_URL + obj.emoticon_name)
    emoticon_icon.short_description = 'Glance'
    emoticon_icon.admin_order_field = 'emoticon_name'

    def author_link(self, obj):
        return format_html(u'<a href="{0}">{1}</a>',
                u'../../{0}/{1}/{2}/'.format(obj.author._meta.app_label, obj.author._meta.module_name, obj.author.id),
                obj.author)
    author_link.short_description = 'Author'
    author_link.admin_order_field = 'author'


class PhotoServerAdmin(admin.ModelAdmin):
    pass

admin.site.register(Photo, PhotoAdmin)
admin.site.register(PendingPhoto, PendingPhotoAdmin)
admin.site.register(Album, AlbumAdmin)
admin.site.register(PhotoComment, PhotoCommentAdmin)
admin.site.register(PhotoGlance, PhotoGlanceAdmin)
admin.site.register(PhotoServer, PhotoServerAdmin)
