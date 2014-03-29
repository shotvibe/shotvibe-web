from django import forms
from django.contrib import admin, auth
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django.utils.html import format_html

from phone_auth.models import User, UserEmail, AuthToken, PhoneNumber, PhoneNumberConfirmSMSCode, PhoneNumberLinkCode, AnonymousPhoneNumber, PhoneContact
from photos.models import AlbumMember

class AuthTokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'description', 'date_created', 'key')
    list_display_links = list_display

class PhoneNumberConfirmSMSCodeInline(admin.TabularInline):
    model = PhoneNumberConfirmSMSCode

class PhoneNumberAdmin(admin.ModelAdmin):
    list_display = ('phone_number', 'user_link', 'date_created', 'verified', 'invite_link_visited')
    list_display_links = ('phone_number', 'date_created')
    search_fields = ('phone_number', 'user__nickname')
    list_filter = ('verified',)

    readonly_fields = ('user', 'date_created')

    inlines = [PhoneNumberConfirmSMSCodeInline]

    def user_link(self, obj):
        return format_html(u'<a href="{0}">{1}</a>',
                u'../../{0}/{1}/{2}/'.format(obj.user._meta.app_label, obj.user._meta.module_name, obj.user.id),
                obj.user)
    user_link.short_description = 'User'
    user_link.admin_order_field = 'user'
    user_link.allow_tags = True

    def invite_link_visited(self, instance):
        try:
            link_code = PhoneNumberLinkCode.objects.get(phone_number=instance)
            return link_code.was_visited
        except PhoneNumberLinkCode.DoesNotExist:
            return None
    invite_link_visited.boolean = True

class PhoneNumberConfirmSMSCodeAdmin(admin.ModelAdmin):
    list_display = ('phone_number', 'confirmation_key', 'confirmation_code', 'date_created')
    list_display_links = list_display

class UserCreationForm(forms.ModelForm):
    """A form for creating new users. Includes all the required
    fields, plus a repeated password."""
    password1 = forms.CharField(label='Password', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Password confirmation', widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ('nickname',)

    def clean_password2(self):
        # Check that the two password entries match
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords don't match")
        return password2

    def save(self, commit=True):
        # Save the provided password in hashed format
        user = super(UserCreationForm, self).save(commit=False)
        # TODO Properly create a new id via make_user_id
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user

class UserChangeForm(forms.ModelForm):
    """A form for updating users. Includes all the fields on
    the user, but replaces the password field with admin's
    password hash display field.
    """
    password = ReadOnlyPasswordHashField(label=("Password"),
        help_text=("Raw passwords are not stored, so there is no way to see "
                    "this user's password, but you can change the password "
                    "using <a href=\"password/\">this form</a>."))

    class Meta:
        model = User

    def clean_password(self):
        # Regardless of what the user provides, return the initial value.
        # This is done here, rather than on the field, because the
        # field does not have access to the initial value
        return self.initial["password"]

class UserEmailInline(admin.TabularInline):
    model = UserEmail

class PhoneNumberInline(admin.TabularInline):
    model = PhoneNumber

class AlbumMemberInline(admin.TabularInline):
    model = AlbumMember
    fk_name = 'user'
    verbose_name = 'Album'
    verbose_name_plural = 'Albums'

    fields = ('album_link', 'added_by_user_link', 'datetime_added', 'last_access')
    readonly_fields = fields

    ordering = ('datetime_added',)

    can_delete = False

    extra = 0
    max_num = 0

    def album_link(self, obj):
        return format_html(u'<a href="{0}">{1}</a>',
                u'../../../{0}/{1}/{2}/'.format(obj.album._meta.app_label, obj.album._meta.module_name, obj.album.id),
                obj.album.name)
    album_link.short_description = 'Album'
    album_link.admin_order_field = 'album'
    album_link.allow_tags = True

    def added_by_user_link(self, obj):
        return format_html(u'<a href="{0}">{1}</a>',
                u'../../../{0}/{1}/{2}/'.format(obj.added_by_user._meta.app_label, obj.added_by_user._meta.module_name, obj.added_by_user.id),
                obj.added_by_user)
    added_by_user_link.short_description = 'Added by user'
    added_by_user_link.admin_order_field = 'added_by_user'
    added_by_user_link.allow_tags = True

class PhoneContactInline(admin.TabularInline):
    model = PhoneContact
    fk_name = 'created_by_user'

    ordering = ('user', 'contact_nickname')

    raw_id_fields = ('anonymous_phone_number', 'user')

    readonly_fields = ('anonymous_phone_number', 'user', 'date_created', 'contact_nickname')

    extra = 0

class UserAdmin(auth.admin.UserAdmin):
    # The fields to be used in displaying the User model.
    # These override the definitions on the base UserAdmin
    # that reference specific fields on auth.User.

    fieldsets = (
        (None, {'fields': ('password',)}),
        ('Personal info', {'fields': ('nickname', 'avatar_full', 'primary_email')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser',
                                       'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('nickname', 'password1', 'password2')}
        ),
    )
    form = UserChangeForm
    add_form = UserCreationForm
    list_display = ('id', 'avatar', 'nickname', 'primary_email', 'first_phone_number', 'first_phone_number_verified', 'invite_link_visited', 'is_staff')
    list_display_links = list_display
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups')
    search_fields = ('id', 'nickname', 'phonenumber__phone_number', 'primary_email__email',)
    ordering = ('id',)
    filter_horizontal = ('groups', 'user_permissions',)

    readonly_fields = ('avatar_full', 'primary_email',)

    inlines = [UserEmailInline, PhoneNumberInline, AlbumMemberInline, PhoneContactInline]

    def first_phone_number(self, instance):
        return instance.phonenumber_set.all()[:1].get()

    def first_phone_number_verified(self, instance):
        phone_number = instance.phonenumber_set.first()
        if phone_number:
            return phone_number.verified
        else:
            return None
    first_phone_number_verified.short_description = 'Verified'
    first_phone_number_verified.boolean = True

    def invite_link_visited(self, instance):
        try:
            link_code = PhoneNumberLinkCode.objects.get(phone_number=self.first_phone_number(instance))
            return link_code.was_visited
        except PhoneNumberLinkCode.DoesNotExist:
            return None
    invite_link_visited.boolean = True

    def avatar(self, instance):
        return format_html(u'<img src="{0}" width="24" height="24">', instance.get_avatar_url(), instance.get_avatar_url())

    def avatar_full(self, instance):
        return format_html(u'<img src="{0}">', instance.get_avatar_url(), instance.get_avatar_url())


#admin.site.unregister(auth.models.Group)

class PhoneNumberLinkCodeAdmin(admin.ModelAdmin):
    list_display = ('phone_number', 'inviting_user', 'date_created', 'invite_code', 'was_visited')
    list_display_links = list_display

    fields = ('phone_number', 'inviting_user', 'date_created', 'invite_link', 'was_visited')
    readonly_fields = ('phone_number', 'inviting_user', 'date_created', 'invite_link', 'was_visited')
    search_fields = ('phone_number__phone_number',)
    list_filter = ('was_visited',)

    def invite_link(self, instance):
        return format_html(u'<a href="{0}">{1}</a>', instance.get_invite_page(), instance.invite_code)

class AnonymousPhoneNumberAdmin(admin.ModelAdmin):
    pass

class PhoneContactAdmin(admin.ModelAdmin):
    pass

admin.site.register(User, UserAdmin)
admin.site.register(AuthToken, AuthTokenAdmin)
admin.site.register(PhoneNumber, PhoneNumberAdmin)
admin.site.register(PhoneNumberConfirmSMSCode, PhoneNumberConfirmSMSCodeAdmin)
admin.site.register(PhoneNumberLinkCode, PhoneNumberLinkCodeAdmin)
admin.site.register(AnonymousPhoneNumber, AnonymousPhoneNumberAdmin)
admin.site.register(PhoneContact, PhoneContactAdmin)
