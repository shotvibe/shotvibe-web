from django.conf import settings

from mixpanel import Mixpanel

from phone_auth.sms_send import in_testing_mode

def track_event(user, event_name, event_properties={}):
    # Don't track events during unit tests
    if in_testing_mode():
        return

    mixpanel_token = getattr(settings, 'MIXPANEL_TOKEN', None)
    if mixpanel_token:
        mixpanel = Mixpanel(mixpanel_token)
        mixpanel.track(str(user.id), event_name, event_properties)
