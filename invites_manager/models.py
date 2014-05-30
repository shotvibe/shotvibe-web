from django.db import models

from phone_auth.models import PhoneNumberLinkCode


class SMSInviteMessageManager(models.Manager):
    def country_calling_code_use_default(self, country_calling_code):
        if SMSInviteMessage.objects.filter(country_calling_code=country_calling_code, time_delay_hours=0).exists():
            return False
        else:
            if not SMSInviteMessage.objects.filter(country_calling_code=None, time_delay_hours=0).exists():
                raise RuntimeError('No default SMSInviteMessage exists in database')
            return True


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

    def __unicode__(self):
        return unicode(self.link_code.phone_number) + ' (' + unicode(self.time_delay_hours) + ' hours)'
