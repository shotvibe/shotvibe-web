import datetime

from photos.models import Photo

#PUBLIC_FEED_TIME_THRESHOLD = datetime.timedelta(days=3)
PUBLIC_FEED_TIME_THRESHOLD = datetime.timedelta(days=90)
PUBLIC_FEED_SCORE_THRESHOLD = 1
PUBLIC_FEED_NUM_PHOTOS = 60

def compute_public_feed(now):
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

    photos = [p for p in original_photos]

    for p in photos:
        p.num_copies = num_copies[p.photo_id]
        p.total_photo_score = total_photo_score[p.photo_id]
        p.age = (now - p.date_created).total_seconds()

    photos.sort(key=photo_points, reverse=True)

    return photos[:PUBLIC_FEED_NUM_PHOTOS]
