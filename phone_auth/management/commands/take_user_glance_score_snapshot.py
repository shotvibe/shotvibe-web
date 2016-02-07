from django.core.management.base import BaseCommand
from django.utils import timezone
from phone_auth.models import UserGlanceScoreSnapshot

class Command(BaseCommand):
    help = 'Take a current snapshot of all user glance scores'

    def handle(self, *args, **options):
        now = timezone.now()
        UserGlanceScoreSnapshot.objects.take_snapshot(now)
        self.stdout.write('Success')
