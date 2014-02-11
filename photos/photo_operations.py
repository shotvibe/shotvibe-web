import Queue
import random
import sys
import threading

from django.conf import settings
from django.db.models import Max
import django.db

from photos.models import Album
from photos.models import PendingPhoto
from photos.models import Photo

all_photo_subdomains = (
        'photos01',
        'photos02',
        'photos03',
        'photos04',
        )

# TODO This module should use be updated to use real background tasks instead
# of a background thread

# See:
#     http://stackoverflow.com/questions/2829329/catch-a-threads-exception-in-the-caller-thread-in-python/6874161#6874161
class ExThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.__status_queue = Queue.Queue()

    def run_with_exception(self):
        """This method should be overriden."""
        raise NotImplementedError

    def run(self):
        """This method should NOT be overriden."""
        try:
            self.run_with_exception()
        except Exception:
            self.__status_queue.put(sys.exc_info())
        self.__status_queue.put(None)

    def wait_for_exc_info(self):
        return self.__status_queue.get()

    def join_with_exception(self):
        ex_info = self.wait_for_exc_info()
        if ex_info is None:
            return
        else:
            raise ex_info[1]


class AddPhotoException(Exception):
    pass


class PhotoNotUploadedAddPhotoException(AddPhotoException):
    pass


class InvalidPhotoIdAddPhotoException(AddPhotoException):
    pass


class AddPendingPhotosToAlbumAction(ExThread):
    def __init__(self, photo_ids, album_id, date_created):
        ExThread.__init__(self)

        self.photo_ids = photo_ids
        self.album_id = album_id
        self.date_created = date_created

    def get_new_photo_ids(self):
        def photo_not_already_added(photo_id):
            try:
                Photo.objects.get(photo_id=photo_id)
            except Photo.DoesNotExist:
                return True
            else:
                return False

        # Skip photos that have already been added
        return filter(photo_not_already_added, self.photo_ids)

    def verify_all_uploaded(self, photo_ids):
        # Make sure that all photos have been already uploaded
        for photo_id in photo_ids:
            try:
                pending_photo = PendingPhoto.objects.get(photo_id=photo_id)
            except PendingPhoto.DoesNotExist:
                raise InvalidPhotoIdAddPhotoException()

            if not pending_photo.is_file_uploaded():
                raise PhotoNotUploadedAddPhotoException()

    def add_photos_to_db(self, photo_ids):
        album = Album.objects.get(pk=self.album_id)
        album_index_q = Photo.objects.filter(album=album).aggregate(Max('album_index'))

        max_album_index = album_index_q['album_index__max']
        if max_album_index is None:
            next_album_index = 0
        else:
            next_album_index = max_album_index + 1

        for photo_id in photo_ids:
            pending_photo = PendingPhoto.objects.get(photo_id=photo_id)

            Photo.objects.create(
                photo_id=photo_id,
                storage_id = pending_photo.storage_id,
                subdomain = random.choice(all_photo_subdomains),
                date_created = self.date_created,
                author=pending_photo.author,
                album=album,
                album_index = next_album_index,
            )

            next_album_index += 1

            pending_photo.delete()

        album.save_revision(self.date_created)

    def run_with_exception(self):
        try:
            self.perform_action()
        finally:
            django.db.close_old_connections()

    def perform_action(self):
        new_photo_ids = self.get_new_photo_ids()

        self.verify_all_uploaded(new_photo_ids)

        if not settings.USING_LOCAL_PHOTOS:
            # TODO Check with the photo upload handler that all photos have completed processing
            pass

        with django.db.transaction.atomic():
            self.add_photos_to_db(new_photo_ids)


def add_pending_photos_to_album(photo_ids, album_id, date_created):
    """
    May throw 'AddPhotoException'
    """

    # TODO This is only current needed to make tests work with sqlite
    # See this bug:
    #     https://code.djangoproject.com/ticket/12118
    if settings.USING_LOCAL_PHOTOS:
        action = AddPendingPhotosToAlbumAction(photo_ids, album_id, date_created)
        action.perform_action()
    else:
        thread = AddPendingPhotosToAlbumAction(photo_ids, album_id, date_created)
        thread.daemon = False
        thread.start()
        thread.join_with_exception()
