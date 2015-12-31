from django.utils import timezone

class LastOnlineMiddleware(object):
    def process_request(self, request):
        if not request.user.is_anonymous():
            request.user.last_online = timezone.now()
            request.user.save(update_fields=['last_online'])
