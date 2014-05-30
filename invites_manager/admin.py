from django.contrib import admin

from invites_manager.models import SMSInviteMessage, ScheduledSMSInviteMessage


class SMSInviteMessageAdmin(admin.ModelAdmin):
    list_display = ('country_calling_code', 'time_delay_hours', 'message_template')
    list_display_links = ('country_calling_code', 'time_delay_hours')

    ordering = ('country_calling_code', 'time_delay_hours')


class ScheduledSMSInviteMessageAdmin(admin.ModelAdmin):
    list_display = ('active', 'phone_number', 'inviting_user', 'time_delay_hours', 'scheduled_delivery_time', 'message_template')

    ordering = ('link_code', 'scheduled_delivery_time')

    def phone_number(self, instance):
        return instance.link_code.phone_number

    def inviting_user(self, instance):
        return instance.link_code.inviting_user

    def active(self, instance):
        return not instance.link_code.was_visited
    active.boolean = True


admin.site.register(SMSInviteMessage, SMSInviteMessageAdmin)
admin.site.register(ScheduledSMSInviteMessage, ScheduledSMSInviteMessageAdmin)
