import datetime

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from photos.models import Album, Photo
from photos import photo_operations

#PUBLIC_FEED_TIME_THRESHOLD = datetime.timedelta(days=3)
PUBLIC_FEED_TIME_THRESHOLD = datetime.timedelta(days=90)
PUBLIC_FEED_SCORE_THRESHOLD = 1
PUBLIC_FEED_NUM_PHOTOS = 60


def update_public_feed():
    """
    Immediately updates the public feed with the current up-to-date content.

    See `compute_public_feed`
    """
    with transaction.atomic():
        now = timezone.now()
        new_photos = compute_public_feed(now)
        set_public_feed(new_photos, now)


def compute_public_feed(now):
    """
    Go throughs all of the photos in the system, and figures out which ones
    should be in the public feed, and in what order, based on a ranking
    algorithm.

    Returns a list of photos
    """
    original_photos = Photo.objects.filter(date_created__gte=now-PUBLIC_FEED_TIME_THRESHOLD, copied_from_photo__isnull=True)
    photo_copies = Photo.objects.filter(date_created__gte=now-PUBLIC_FEED_TIME_THRESHOLD, copied_from_photo__isnull=False)

    num_copies = {}
    total_photo_score = {}

    for p in original_photos:
        num_copies[p.photo_id] = 0
        total_photo_score[p.photo_id] = p.photo_glance_score

    for p in photo_copies:
        try:
            num_copies[p.copied_from_photo.photo_id] += 1
            total_photo_score[p.copied_from_photo.photo_id] += p.photo_glance_score
        except KeyError:
            pass

    def photo_points(photo):
        x = num_copies[photo.photo_id]
        y = total_photo_score[photo.photo_id]
        z = (now - photo.date_created).total_seconds()
        # TODO:
        return y

    photos = [p for p in original_photos if total_photo_score[p.photo_id] >= PUBLIC_FEED_SCORE_THRESHOLD]

    for p in photos:
        p.num_copies = num_copies[p.photo_id]
        p.total_photo_score = total_photo_score[p.photo_id]
        p.age = (now - p.date_created).total_seconds()

    photos.sort(key=photo_points, reverse=True)

    return photos[:PUBLIC_FEED_NUM_PHOTOS]


def set_public_feed(new_photos, now):
    """
    Sets the public feed album to contain the given list of photos.  The photos
    will be copied into the public feed. If the public feed already contains
    any of the given photos, then they will not be overwritten (but their rank
    will be appropriately updated)
    """
    new_photo_ids = set()
    for p in new_photos:
        new_photo_ids.add(p.photo_id)

    public_feed_album = Album.objects.get(pk=settings.PUBLIC_ALBUM_ID)
    old_photos = Photo.objects.filter(album=public_feed_album)

    existing_photo_ids = {}

    # Large constant that should be bigger than the maximum size of an album.
    # Used to re-arrange the order (album_index) of photos
    i = 100000000

    for p in old_photos:
        photo_id = p.get_original_photo().photo_id

        if photo_id in new_photo_ids:
            # This existing photo should be moved to its new rank in the public
            # feed
            existing_photo_ids[photo_id] = p

            # We move it into a temporary position for now, and later will move
            # it to its correct album_index
            p.album_index = i
            p.save(update_fields=['album_index'])

            i += 1
        else:
            # This existing photo no longer ranks in the public feed and should
            # be deleted
            p.delete()

    # Dictionary from subdomain values to lists of Photo objects
    added_photos = {}

    i = 0
    for p in new_photos:
        if p.photo_id in existing_photo_ids:
            # Photo already exists in the public feed. We just need to move it
            # to the correct position

            photo = existing_photo_ids[p.photo_id]
            photo.album_index = i
            photo.save(update_fields=['album_index'])
        else:
            # Photo does not exist in the public feed. We need to copy it in

            new_photo = p.create_copy(p.author, public_feed_album, i, now)
            chosen_subdomain = new_photo.subdomain
            if chosen_subdomain in added_photos:
                added_photos[chosen_subdomain].append(new_photo)
            else:
                added_photos[chosen_subdomain] = [new_photo]

            # TODO: A new Photo made it into the public feed!
            # 1. Update the score of the user who uploaded the photo
            # 2. Send push notification to the user

        i += 1

    photo_operations.update_all_photo_servers(added_photos)
