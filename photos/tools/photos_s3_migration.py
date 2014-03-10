import os

from boto.s3.connection import S3Connection
from boto.s3.key import Key

from django.conf import settings

from photos.photo_operations import choose_random_subdomain
from photos.models import Photo


def migrate_photos_to_s3(s3_bucket_name, aws_access_key, aws_secret_access_key):
    """
    This is used to copy legacy photos stored on the server in
    LOCAL_PHOTO_BUCKETS_BASE_PATH to the new photo storage system that stores
    the photos in an AWS S3 bucket.

    This should be run manually, ideally with the server shut down.
    """
    print 'Connecting to bucket: ' + s3_bucket_name

    conn = S3Connection(aws_access_key, aws_secret_access_key)

    s3_bucket = conn.get_bucket(s3_bucket_name)

    old_buckets = get_all_old_photo_buckets()

    # The default string set by the migration is 'temporary-placeholder'
    old_photos_collection = Photo.objects.filter(storage_id__exact='temporary-placeholder')

    total_photos = old_photos_collection.count()

    print 'Total number of photos: ' + str(total_photos)

    for index, photo in enumerate(old_photos_collection):
        print 'Migrating ' + str(index + 1) + '/' + str(total_photos)
        if photo.subdomain != 'temporary-placeholder':
            raise RuntimeError('Inconsistent photo: ' + str(photo))
        migrate_photo(old_buckets, s3_bucket, photo)

    print 'All Done. Success!'


def migrate_photo(old_buckets, s3_bucket, photo):
    print 'Migrating photo: ' + str(photo)
    old_photo_bucket = find_photo_bucket(old_buckets, photo.photo_id)

    new_subdomain = choose_random_subdomain()
    new_storage_id = Photo.generate_photo_id()
    print 'New subdomain: ' + new_subdomain
    print 'New storage_id: ' + new_storage_id

    def upload(ext):
        filename = os.path.join(settings.LOCAL_PHOTO_BUCKETS_BASE_PATH, old_photo_bucket, photo.photo_id + ext)
        print 'Uploading: ' + filename

        key = Key(s3_bucket, new_storage_id + ext)
        key.metadata = { 'Content-Type': 'image/jpeg' }
        key.set_contents_from_filename(filename)
        key.close()

    upload('.jpg')
    for ext in all_photo_extensions:
        upload('_' + ext + '.jpg')

    photo.subdomain = new_subdomain
    photo.storage_id = new_storage_id
    photo.save(update_fields=['subdomain', 'storage_id'])


def find_photo_bucket(old_buckets, photo_id):
    for old_bucket in old_buckets:
        filename = os.path.join(settings.LOCAL_PHOTO_BUCKETS_BASE_PATH, old_bucket, photo_id + '.jpg')
        if os.path.isfile(filename):
            return old_bucket
    raise RuntimeError('Photo not found in any buckets: ' + photo_id)


def get_all_old_photo_buckets():
    return get_all_subdirs(settings.LOCAL_PHOTO_BUCKETS_BASE_PATH)


def get_all_subdirs(dir):
    return [name for name in os.listdir(dir)
            if os.path.isdir(os.path.join(dir, name))]


all_photo_extensions = [
        'r_qvga',
        'r_hvga',
        'r_vga',
        'r_wvga',
        'r_qhd',
        'r_dvga',
        'r_dvgax',
        'r_hd',
        'r_xga',
        'r_wxga',
        'r_fhd',
        'r_qxga',
        'r_wqxga',
        'thumb75',
        'iphone3',
        'iphone4',
        'iphone5',
        'crop140',
        '940x570'
    ]
