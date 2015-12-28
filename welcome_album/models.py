import datetime

from django.conf import settings
from django.db import models

WELCOME_ALBUM_DELAY = datetime.timedelta(seconds=10)

class ScheduledWelcomeAlbumJobManager(models.Manager):
    def get_scheduled_till(self, time):
        return ScheduledWelcomeAlbumJob.objects.filter(scheduled_job_time__lte=time)

    def schedule_job(self, new_user, current_time):
        if not settings.WELCOME_ALBUM_ID:
            return

        ScheduledWelcomeAlbumJob.objects.create(
                scheduled_job_time = current_time + WELCOME_ALBUM_DELAY,
                new_user = new_user)


class ScheduledWelcomeAlbumJob(models.Model):
    scheduled_job_time = models.DateTimeField(db_index=True)
    new_user = models.ForeignKey(settings.AUTH_USER_MODEL)

    objects = ScheduledWelcomeAlbumJobManager()

    def __unicode__(self):
        return '(' + unicode(self.scheduled_job_time) + ')'
