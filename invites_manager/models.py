import datetime
import string

from django.db import models

import phonenumbers

from phone_auth.models import PhoneNumberLinkCode
from photos.models import Album
import phone_auth.sms_send


class SMSInviteMessageManager(models.Manager):
    def country_calling_code_use_default(self, country_calling_code):
        if SMSInviteMessage.objects.filter(country_calling_code=country_calling_code, time_delay_hours=0).exists():
            return False
        else:
            if not SMSInviteMessage.objects.filter(country_calling_code=None, time_delay_hours=0).exists():
                raise RuntimeError('No default SMSInviteMessage exists in database')
            return True

    def invite_new_user(self, sms_invite_processor, link_code, current_time):
        destination_phone_number = link_code.phone_number.phone_number
        destination_country_calling_code = phonenumbers.parse(destination_phone_number).country_code

        if SMSInviteMessage.objects.country_calling_code_use_default(destination_country_calling_code):
            immediate_message_obj = SMSInviteMessage.objects.get(country_calling_code=None, time_delay_hours=0)
            delayed_message_objs = SMSInviteMessage.objects.filter(country_calling_code=None, time_delay_hours__gt=0)
        else:
            immediate_message_obj = SMSInviteMessage.objects.get(country_calling_code=destination_country_calling_code, time_delay_hours=0)
            delayed_message_objs = SMSInviteMessage.objects.filter(country_calling_code=destination_country_calling_code, time_delay_hours__gt=0)

        for delayed_message in delayed_message_objs:
            ScheduledSMSInviteMessage.objects.create(
                    invite_sent_time = current_time,
                    scheduled_delivery_time = current_time + datetime.timedelta(hours=delayed_message.time_delay_hours),
                    link_code = link_code,
                    message_template = delayed_message.message_template,
                    time_delay_hours = delayed_message.time_delay_hours,
                    sms_sender_phone_override = None)

        sms_invite_processor.send_immediate_invite(link_code, immediate_message_obj.message_template, None)


class SMSInviteMessage(models.Model):
    country_calling_code = models.PositiveSmallIntegerField(null=True, blank=True, help_text=
            'See <a href="http://en.wikipedia.org/wiki/List_of_country_calling_codes">Full List</a>. If blank then this will be the default')
    message_template = models.TextField(help_text=
            'Available variables: <code>${inviter} ${name} ${album}</code>')
    time_delay_hours = models.PositiveIntegerField(help_text=
            'Numbers of hours to wait after initial invitation before sending this message')

    class Meta:
        unique_together = ('country_calling_code', 'time_delay_hours')

    objects = SMSInviteMessageManager()


class ScheduledSMSInviteMessageManager(models.Manager):
    def get_scheduled_till(self, time):
        return ScheduledSMSInviteMessage.objects.filter(scheduled_delivery_time__lte=time)


class ScheduledSMSInviteMessage(models.Model):
    invite_sent_time = models.DateTimeField()
    scheduled_delivery_time = models.DateTimeField(db_index=True)
    link_code = models.ForeignKey(PhoneNumberLinkCode)
    message_template = models.TextField()
    time_delay_hours = models.PositiveIntegerField()
    sms_sender_phone_override = models.CharField(max_length=32, null=True, blank=True)

    objects = ScheduledSMSInviteMessageManager()


class SMSInviteProcessor(object):
    def __init__(self, sms_sender=phone_auth.sms_send.send_sms):
        """
        sms_sender must be a callable with the same signature as phone_auth.sms_send.send_sms
        """
        self.sms_sender = sms_sender

    def send_immediate_invite(self, link_code, message_template, sms_sender_phone_override):
        destination_phone = link_code.phone_number.phone_number

        if sms_sender_phone_override:
            sender_phone = sms_sender_phone_override
        else:
            inviter_phone = link_code.inviting_user.get_primary_phone_number()
            if inviter_phone:
                sender_phone = inviter_phone.phone_number
            else:
                sender_phone = None

        # For showing the album, just grab the first album that the user belongs to
        album = Album.objects.get_user_albums(link_code.phone_number.user.id)[0]

        message = string.Template(message_template).safe_substitute(
                inviter = link_code.inviting_user.nickname,
                name = link_code.phone_number.user.nickname,
                album = album)

        invite_url_prefix = 'https://useglance.com'
        link = link_code.get_invite_page(invite_url_prefix)

        final_sms_message = message + '\n' + link
        self.sms_sender(destination_phone, final_sms_message, sender_phone)

    def process_scheduled_invites(self, current_time):
        for scheduled_message in ScheduledSMSInviteMessage.objects.get_scheduled_till(current_time):
            self.send_immediate_invite(scheduled_message.link_code, scheduled_message.message_template, scheduled_message.sms_sender_phone_override)
            scheduled_message.delete()
