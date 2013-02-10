from django import forms
from django.contrib import admin, auth
from django.contrib.auth.forms import ReadOnlyPasswordHashField

from phone_auth.models import User, UserEmail, AuthToken, PhoneNumber, PhoneNumberConfirmSMSCode

class AuthTokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'description', 'date_created', 'key')
    list_display_links = list_display

class PhoneNumberConfirmSMSCodeInline(admin.TabularInline):
    model = PhoneNumberConfirmSMSCode

class PhoneNumberAdmin(admin.ModelAdmin):
    list_display = ('phone_number', 'user', 'date_created', 'verified')
    list_display_links = list_display

    inlines = [PhoneNumberConfirmSMSCodeInline]

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

class UserAdmin(auth.admin.UserAdmin):
    # The fields to be used in displaying the User model.
    # These override the definitions on the base UserAdmin
    # that reference specific fields on auth.User.

    fieldsets = (
        (None, {'fields': ('password',)}),
        ('Personal info', {'fields': ('nickname', 'primary_email')}),
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
    list_display = ('id', 'nickname', 'is_registered', 'primary_email', 'is_staff')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'is_registered', 'groups')
    search_fields = ('nickname', 'primary_email',)
    ordering = ('id',)
    filter_horizontal = ('groups', 'user_permissions',)

    inlines = [UserEmailInline]

#admin.site.unregister(auth.models.Group)

admin.site.register(User, UserAdmin)
admin.site.register(AuthToken, AuthTokenAdmin)
admin.site.register(PhoneNumber, PhoneNumberAdmin)
admin.site.register(PhoneNumberConfirmSMSCode, PhoneNumberConfirmSMSCodeAdmin)
