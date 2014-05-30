from django.contrib import admin

from invites_manager.models import SMSInviteMessage


class SMSInviteMessageAdmin(admin.ModelAdmin):
    list_display = ('country_calling_code', 'time_delay_hours', 'message_template')
    list_display_links = ('country_calling_code', 'time_delay_hours')

    ordering = ('country_calling_code', 'time_delay_hours')


admin.site.register(SMSInviteMessage, SMSInviteMessageAdmin)
