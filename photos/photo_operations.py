import Queue
import random
import sys
import threading
import time
import json

from django.conf import settings
from django.db.models import Max
from django.db import IntegrityError
from django.db import transaction
from django.db import connection
import django.db

import requests

from photos.models import Album
from photos.models import PendingPhoto
from photos.models import Photo
from photos.models import PhotoServer


def choose_random_subdomain():
    return random.choice(settings.ALL_PHOTO_SUBDOMAINS)


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
        """
        Returns a dictionary from subdomain values to lists of Photo objects
        """
        added_photos = {}

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
                        chosen_subdomain = choose_random_subdomain()
                        p = Photo.objects.create(
                            photo_id=photo_id,
                            storage_id = pending_photo.storage_id,
                            subdomain = chosen_subdomain,
                            date_created = self.date_created,
                            author=pending_photo.author,
                            album=album,
                            album_index = next_album_index,
                        )
                        if chosen_subdomain in added_photos:
                            added_photos[chosen_subdomain].append(p)
                        else:
                            added_photos[chosen_subdomain] = [p]
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

        return added_photos

    def run_with_exception(self):
        try:
            self.perform_action()
        finally:
            django.db.close_old_connections()

    def perform_action(self):
        self.verify_all_uploaded(self.photo_ids)

        if not settings.USING_LOCAL_PHOTOS:
            retry_count = 2
            while not self.all_processing_done(self.photo_ids):
                # TODO This should be more robust and also "kick" the photo
                # upload server to make sure that no jobs got lost and to
                # re-prioritize jobs

                retry_count -= 1
                if retry_count == 0:
                    # TODO This should instead return an appropriate HTTP status code
                    raise RuntimeError('Photo Processing Timeout: ' + str(self.photo_ids))

                RETRY_TIME = 1

                time.sleep(RETRY_TIME)

        with transaction.atomic():
            success = False
            while not success:
                try:
                    with transaction.atomic():
                        added_photos = self.add_photos_to_db(self.photo_ids)
                except IntegrityError:
                    success = False
                else:
                    success = True

            for subdomain, photos in added_photos.iteritems():
                for photo_server in PhotoServer.objects.filter(subdomain=subdomain, unreachable=False):
                    # TODO We should use concurrent requests for this

                    num_retries = 5
                    initial_retry_time = 4

                    try:
                        request_with_n_retries(num_retries, initial_retry_time,
                                lambda: photo_server_set_photos(photo_server.photos_update_url, photo_server.auth_key, photos))
                    except requests.exceptions.RequestException:
                        # TODO Log this
                        photo_server.set_unreachable()


            album = Album.objects.get(pk=self.album_id)
            album.save_revision(self.date_created)


class CopyPhotosToAlbumAction(ExThread):
    def __init__(self, author, photo_ids, album_id, date_created):
        ExThread.__init__(self)

        self.author = author
        self.photo_ids = photo_ids
        self.album_id = album_id
        self.date_created = date_created

    def add_photos_to_db(self, photo_ids):
        """
        Returns a dictionary from subdomain values to lists of Photo objects
        """
        added_photos = {}

        album = Album.objects.get(pk=self.album_id)
        album_index_q = Photo.objects.filter(album=album).aggregate(Max('album_index'))

        max_album_index = album_index_q['album_index__max']
        if max_album_index is None:
            next_album_index = 0
        else:
            next_album_index = max_album_index + 1

        for photo_id in photo_ids:
            try:
                photo = Photo.objects.get(photo_id=photo_id)
            except Photo.DoesNotExist:
                # Silently ignore any non-existing photo_ids
                pass
            else:
                if not Photo.objects.filter(
                        album=album,
                        storage_id=photo.storage_id,
                        author=self.author).exists():
                    chosen_subdomain = choose_random_subdomain()
                    p = Photo.objects.create(
                        photo_id=Photo.generate_photo_id(),
                        storage_id = photo.storage_id,
                        subdomain = chosen_subdomain,
                        date_created = self.date_created,
                        author=self.author,
                        album=album,
                        album_index = next_album_index,
                    )
                    if chosen_subdomain in added_photos:
                        added_photos[chosen_subdomain].append(p)
                    else:
                        added_photos[chosen_subdomain] = [p]

                    if PendingPhoto.objects.filter(photo_id=p.photo_id).exists():
                        raise IntegrityError

                    next_album_index += 1

        return added_photos

    def run_with_exception(self):
        try:
            self.perform_action()
        finally:
            django.db.close_old_connections()

    def perform_action(self):
        with transaction.atomic():
            success = False
            while not success:
                try:
                    with transaction.atomic():
                        added_photos = self.add_photos_to_db(self.photo_ids)
                except IntegrityError:
                    success = False
                else:
                    success = True

            for subdomain, photos in added_photos.iteritems():
                for photo_server in PhotoServer.objects.filter(subdomain=subdomain, unreachable=False):
                    # TODO We should use concurrent requests for this

                    num_retries = 5
                    initial_retry_time = 4

                    try:
                        request_with_n_retries(num_retries, initial_retry_time,
                                lambda: photo_server_set_photos(photo_server.photos_update_url, photo_server.auth_key, photos))
                    except requests.exceptions.RequestException:
                        # TODO Log this
                        photo_server.set_unreachable()


            album = Album.objects.get(pk=self.album_id)
            album.save_revision(self.date_created)


def request_with_n_retries(num_retries, initial_retry_time, action):
    num_retries_left = num_retries
    retry_time = initial_retry_time
    while True:
        try:
            return action()
        except requests.exceptions.RequestException:
            if num_retries_left > 0:
                time.sleep(retry_time)
                retry_time *= 2
                num_retries_left -= 1
            else:
                raise


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


def copy_photos_to_album(author, photo_ids, album_id, date_created):
    # TODO This is only current needed to make tests work with sqlite
    # See this bug:
    #     https://code.djangoproject.com/ticket/12118
    if settings.USING_LOCAL_PHOTOS:
        action = CopyPhotosToAlbumAction(author, photo_ids, album_id, date_created)
        action.perform_action()
    else:
        thread = CopyPhotosToAlbumAction(author, photo_ids, album_id, date_created)
        thread.daemon = False
        thread.start()
        thread.join_with_exception()


def is_postgresql(conn):
    return conn.settings_dict['ENGINE'].rsplit('.', 1)[-1] == 'postgresql_psycopg2'

def register_photo_server(photos_update_url, subdomain, auth_key, date_registered):
    # We need to lock the Photo table to make sure that nothing is changed
    # between the time we send it the current data and the time we register it
    # in the database.

    if is_postgresql(connection):
        # This mode will only block concurrent writes to the table
        lock_mode = 'SHARE'

        cursor = connection.cursor()
        cursor.execute('LOCK TABLE %s IN %s MODE' % (connection.ops.quote_name(Photo._meta.db_table), lock_mode))

    all_subdomain_photos = Photo.objects.filter(subdomain=subdomain)

    photo_server_set_photos(photos_update_url, auth_key, all_subdomain_photos)

    obj, created = PhotoServer.objects.get_or_create(
            photos_update_url = photos_update_url,
            defaults = {
                'subdomain': subdomain,
                'auth_key': auth_key,
                'date_registered': date_registered,
                'unreachable': False
                })
    if not created:
        obj.subdomain = subdomain
        obj.auth_key = auth_key
        obj.date_registered = date_registered
        obj.unreachable = False
        obj.save()


def photo_server_set_photos(photos_update_url, photo_server_auth_key, photos):
    body = []
    for p in photos:
        body.append({
            'cmd': 'set',
            'key': p.photo_id,
            'value': p.storage_id,
            })

    r = requests.post(photos_update_url,
            headers = { 'Authorization': 'Key ' + photo_server_auth_key },
            data = json.dumps(body))
    r.raise_for_status()

def photo_server_delete_photos(photos_update_url, photo_server_auth_key, photo_ids):
    # TODO ...
    pass
