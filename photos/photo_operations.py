import Queue
import random
import sys
import threading
import time

from django.conf import settings
from django.db.models import Max
from django.db import IntegrityError
from django.db import transaction
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

    def verify_all_uploaded(self, photo_ids):
        # Make sure that all photos have been already uploaded
        for photo_id in photo_ids:
            try:
                pending_photo = PendingPhoto.objects.get(photo_id=photo_id)
            except PendingPhoto.DoesNotExist:
                # If there is no PendingPhoto but there is a Photo, then we are ok
                try:
                    Photo.objects.get(photo_id=photo_id)
                except Photo.DoesNotExist:
                    raise InvalidPhotoIdAddPhotoException()
                else:
                    pass
            else:
                if not pending_photo.is_file_uploaded():
                    raise PhotoNotUploadedAddPhotoException()

    def all_processing_done(self, photo_ids):
        for photo_id in photo_ids:
            try:
                pending_photo = PendingPhoto.objects.get(photo_id=photo_id)
            except PendingPhoto.DoesNotExist:
                # If there is no PendingPhoto but there is a Photo, then we are ok
                try:
                    Photo.objects.get(photo_id=photo_id)
                except Photo.DoesNotExist:
                    raise InvalidPhotoIdAddPhotoException()
                else:
                    pass
            else:
                if not pending_photo.is_processing_done():
                    return False

        return True

    def add_photos_to_db(self, photo_ids):
        album = Album.objects.get(pk=self.album_id)
        album_index_q = Photo.objects.filter(album=album).aggregate(Max('album_index'))

        max_album_index = album_index_q['album_index__max']
        if max_album_index is None:
            next_album_index = 0
        else:
            next_album_index = max_album_index + 1

        for photo_id in photo_ids:
            try:
                pending_photo = PendingPhoto.objects.get(photo_id=photo_id)
            except PendingPhoto.DoesNotExist:
                try:
                    Photo.objects.get(pk=photo_id)
                except Photo.DoesNotExist:
                    raise InvalidPhotoIdAddPhotoException()
                else:
                    pass
            else:
                try:
                    with transaction.atomic():
                        Photo.objects.create(
                            photo_id=photo_id,
                            storage_id = pending_photo.storage_id,
                            subdomain = random.choice(all_photo_subdomains),
                            date_created = self.date_created,
                            author=pending_photo.author,
                            album=album,
                            album_index = next_album_index,
                        )
                except IntegrityError:
                    t, v, tb = sys.exc_info()
                    # Two possible scenarios:
                    #
                    # 1)  The album_index we tried to add was already added (by a
                    #     concurrent request)
                    #
                    # 2)  photo_id was already added (by a concurrent request)

                    try:
                        Photo.objects.get(pk=photo_id)
                    except Photo.DoesNotExist:
                        # This is most likely case (1). We let the original
                        # exception bubble up (the calling code will retry this function)
                        raise t, v, tb
                    else:
                        # This is case (2)
                        # The photo is already added, so there is nothing to do
                        pass
                else:
                    # Notice that this is only incremented if a new object was
                    # actually inserted
                    next_album_index += 1

                # This is safe to call even if it was already deleted by a
                # concurrent request (will be a nop)
                pending_photo.delete()

    def run_with_exception(self):
        try:
            self.perform_action()
        finally:
            django.db.close_old_connections()

    def perform_action(self):
        self.verify_all_uploaded(self.photo_ids)

        if not settings.USING_LOCAL_PHOTOS:
            while not self.all_processing_done(self.photo_ids):
                # TODO This should be more robust and also "kick" the photo
                # upload server to make sure that no jobs got lost and to
                # re-prioritize jobs

                RETRY_TIME = 1

                time.sleep(RETRY_TIME)

        with transaction.atomic():
            success = False
            while not success:
                try:
                    with transaction.atomic():
                        self.add_photos_to_db(self.photo_ids)
                except IntegrityError:
                    success = False
                else:
                    success = True

            album = Album.objects.get(pk=self.album_id)
            album.save_revision(self.date_created)


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
