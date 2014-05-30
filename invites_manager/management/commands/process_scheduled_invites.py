from django.core.management.base import BaseCommand
from django.utils import timezone

import invites_manager


class Command(BaseCommand):
    help = 'Send any scheduled invites using the invites_manager'

    def handle(self, *args, **options):
        now = timezone.now()
        num_sent = invites_manager.process_scheduled_invites(now)
        self.stdout.write('Successfully sent %d invites' % num_sent)
