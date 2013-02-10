import codecs
import random
import datetime
import glob

from django.contrib import auth
from django.db import transaction
from django.utils.timezone import utc

from photos import image_uploads
from photos.models import Album, Photo, PendingPhoto
from photos.tests import read_in_chunks

def generate_random_data(words_file='/usr/share/dict/words', num_albums=100, num_photos=1000, user_ids=None):
    if not user_ids:
        all_users = auth.get_user_model().objects.all()
        user_ids = [user.id for user in all_users]

    with codecs.open(words_file, 'r', 'utf8') as f:
        words = [line.strip() for line in f]

    base_time = datetime.datetime(2010, 1, 1, tzinfo=utc)

    test_photos = glob.glob('photos/test_photos/*.jpg')

    with transaction.commit_on_success():
        albums = []
        for i in xrange(num_albums):
            creator = auth.get_user_model().objects.get(pk=random.choice(user_ids))
            num_words = random.randint(1, 5)
            name = u' '.join([random.choice(words) for x in range(num_words)])
            date_created = base_time - datetime.timedelta(seconds=random.randint(0, 60*60*24*365))
            new_album = Album.objects.create_album(creator, name, date_created)
            albums.append(new_album)

        for i in xrange(num_photos):
            album = random.choice(albums)
            author = auth.get_user_model().objects.get(pk=random.choice(user_ids))
            date_created = album.last_updated + datetime.timedelta(seconds=random.randint(0, 60*60*24*30))

            photo_id = Photo.objects.upload_request(author)

            location, directory = PendingPhoto.objects.get(photo_id=photo_id).bucket.split(':')
            if location != 'local':
                raise ValueError('Unknown photo bucket location: ' + location)

            with open(random.choice(test_photos)) as f:
                image_uploads.handle_file_upload(directory, photo_id, read_in_chunks(f))

            # Pretend that the photo was uploaded
            Photo.objects.upload_to_album(photo_id, album, date_created)

        max_album_members = 20

        for a in albums:
            other_users = [x for x in user_ids if x != a.creator.id]
            random_users = random.sample(other_users, random.randint(0, min(max_album_members, len(other_users))))
            a.members.add(*random_users)
