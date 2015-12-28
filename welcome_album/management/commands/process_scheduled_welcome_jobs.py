from django.core.management.base import BaseCommand
from django.utils import timezone

import welcome_album


class Command(BaseCommand):
    help = 'Create any scheduled Welcome Albums'

    def handle(self, *args, **options):
        now = timezone.now()
        num_ran = welcome_album.process_scheduled_jobs(now)
        self.stdout.write('Successfully ran %d jobs' % num_ran)
