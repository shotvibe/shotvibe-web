import datetime
import string

import phonenumbers

from phone_auth.models import PhoneNumberLinkCode
from photos.models import Album
import phone_auth.sms_send
from analytics.event_tracking import track_event

from invites_manager.models import SMSInviteMessage, ScheduledSMSInviteMessage


def send_invite(inviter, phone_number, current_time):
    link_code, created = PhoneNumberLinkCode.objects.get_or_create(phone_number=phone_number, defaults={
        'invite_code': PhoneNumberLinkCode.generate_invite_code(),
        'inviting_user': inviter,
        'date_created': current_time,
        'was_visited': False
        })
    if not created:
        # If the target user was previously invited, update his link_code
        # object so that the inviter reflects the user who most recently
        # invited him
        link_code.inviting_user = inviter
        link_code.save(update_fields=['inviting_user'])

        # Delete any scheduled invites that the target user may already
        # have. New scheduled events will be set for the current invite
        ScheduledSMSInviteMessage.objects.filter(link_code=link_code).delete()

    destination_country_calling_code = phonenumbers.parse(phone_number.phone_number).country_code

    if SMSInviteMessage.objects.country_calling_code_use_default(destination_country_calling_code):
        immediate_message_obj = SMSInviteMessage.objects.get(country_calling_code=SMSInviteMessage.COUNTRY_DEFAULT_VALUE, time_delay_hours=0)
        delayed_message_objs = SMSInviteMessage.objects.filter(country_calling_code=SMSInviteMessage.COUNTRY_DEFAULT_VALUE, time_delay_hours__gt=0)
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

    send_immediate_invite(link_code, immediate_message_obj.message_template, None)
    track_event(link_code.phone_number.user, 'New User SMS Invite Sent', {
        'inviter': link_code.inviting_user.id,
        'time_delay_hours': 0})

    return link_code


def send_immediate_invite(link_code, message_template, sms_sender_phone_override):
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
            album = album.name)

    invite_url_prefix = 'https://i.useglance.com'
    link = link_code.get_invite_page(invite_url_prefix)

    final_sms_message = message + '\n' + link
    phone_auth.sms_send.send_sms(destination_phone, final_sms_message, sender_phone)


def process_scheduled_invites(current_time):
    num_sent = 0
    for scheduled_message in ScheduledSMSInviteMessage.objects.get_scheduled_till(current_time):
        if not scheduled_message.link_code.was_visited:
            send_immediate_invite(scheduled_message.link_code, scheduled_message.message_template, scheduled_message.sms_sender_phone_override)
            track_event(scheduled_message.link_code.phone_number.user, 'New User SMS Invite Sent', {
                'inviter': scheduled_message.link_code.inviting_user.id,
                'time_delay_hours': scheduled_message.time_delay_hours})

            num_sent += 1

        scheduled_message.delete()

    return num_sent
