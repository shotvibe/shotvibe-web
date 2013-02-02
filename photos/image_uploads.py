from django.conf import settings

import os, errno

def process_uploaded_image(bucket, photo_id):
    # TODO open the image and resize it to all sizes

    # return temporary dummy width and height:
    return (640, 480)

def handle_file_upload(directory, photo_id, chunks):
    bucket_directory = os.path.join(settings.LOCAL_PHOTO_BUCKETS_BASE_PATH, directory)
    mkdir_p(bucket_directory)
    save_file_path = os.path.join(bucket_directory, photo_id + '.jpg')

    with open(save_file_path, 'wb') as f:
        for chunk in chunks:
            f.write(chunk)

# Taken from <http://stackoverflow.com/a/600612>
def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc: # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else: raise
