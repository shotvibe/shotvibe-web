from django.contrib import admin

from phone_auth.models import AuthToken, PhoneNumber, PhoneNumberConfirmSMSCode

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

admin.site.register(AuthToken, AuthTokenAdmin)
admin.site.register(PhoneNumber, PhoneNumberAdmin)
admin.site.register(PhoneNumberConfirmSMSCode, PhoneNumberConfirmSMSCodeAdmin)
