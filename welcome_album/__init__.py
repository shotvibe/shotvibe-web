from django.conf import settings
from django.db import transaction
import django.db

from photos import photo_operations
from photos.models import Album
from welcome_album.models import ScheduledWelcomeAlbumJob

def create_welcome_album(new_user, current_time):
    template_album = Album.objects.get(pk=settings.WELCOME_ALBUM_ID)

    photo_ids = [p.photo_id for p in template_album.get_photos()]

    now = current_time

    class CreateAlbumAction(photo_operations.ExThread):
        def run_with_exception(self):
            try:
                self.perform_action()
            finally:
                django.db.close_old_connections()

        def perform_action(self):
            with transaction.atomic():
                self.new_album = Album.objects.create_album(template_album.creator, template_album.name, now)
                with self.new_album.modify(now) as m:
                    m.add_user_id(template_album.creator, new_user.id)

    action = CreateAlbumAction()
    # TODO This is only current needed to make tests work with sqlite
    # See this bug:
    #     https://code.djangoproject.com/ticket/12118
    if settings.USING_LOCAL_PHOTOS:
        action.perform_action()
    else:
        action.daemon = False
        action.start()
        action.join_with_exception()

    photo_operations.copy_photos_to_album(template_album.creator, photo_ids, action.new_album.id, now)


def process_scheduled_jobs(current_time):
    num_sent = 0
    for scheduled_job in ScheduledWelcomeAlbumJob.objects.get_scheduled_till(current_time):
        create_welcome_album(scheduled_job.new_user, current_time)
        num_sent += 1
        scheduled_job.delete()

    return num_sent
