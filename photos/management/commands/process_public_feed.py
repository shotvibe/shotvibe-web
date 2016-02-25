from django.core.management.base import BaseCommand

from photos import public_feed

class Command(BaseCommand):
    help = 'Update the contents of the public feed using the ranking algorithm'

    def handle(self, *args, **options):
        public_feed.update_public_feed()
        self.stdout.write('Successfully updated public feed')
