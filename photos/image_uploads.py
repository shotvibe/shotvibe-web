import abc
from PIL import Image
from PIL import ImageOps

from django.conf import settings

import os, errno

class ImageDimensions(object):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def get_image_dimensions(self, width, height):
        """
        Returns a (width, height) tuple of the dimensions that the image should
        be resized to
        """
        return

class BoxMixin(object):
    def __init__(self, box_width, box_height):
        self.box_width = box_width
        self.box_height = box_height

class BoxFitExpanded(ImageDimensions, BoxMixin):
    def get_image_dimensions(self, width, height):
        if width * self.box_height > self.box_width * height:
            new_height = self.box_height
            new_width = new_height * width / height
        else:
            new_width = self.box_width
            new_height = new_width * height / width
        return (new_width, new_height)

class BoxFitCrop(ImageDimensions, BoxMixin):
    def get_image_dimensions(self, width, height):
        return (self.box_width, self.box_height)

class BoxFitConstrain(ImageDimensions, BoxMixin):
    def get_image_dimensions(self, width, height):
        if width * self.box_height > self.box_width * height:
            new_width = self.box_width
            new_height = new_width * height / width
        else:
            new_height = self.box_height
            new_width = new_height * width / height
        return (new_width, new_height)

class BoxFitWithRotation(ImageDimensions, BoxMixin):
    def fit(self, width, height):
        if width * self.box_height > self.box_width * height:
            new_width = self.box_width
            new_height = new_width * height / width
        else:
            new_height = self.box_height
            new_width = new_height * width / height
        return (new_width, new_height)

    def get_image_dimensions(self, width, height):
        landscape_width, landscape_height = self.fit(width, height)
        portrait_height, portrait_width = self.fit(height, width)

        if landscape_width > portrait_width or landscape_height > portrait_height:
            return (landscape_width, landscape_height)
        else:
            return (portrait_width, portrait_height)

def only_shrink(image_dimensions_klass):
    class OnlyShrink(image_dimensions_klass):
        def get_image_dimensions(self, width, height):
            (new_width, new_height) = super(OnlyShrink, self).get_image_dimensions(width, height)
            if new_width <= width and new_height <= height:
                return (new_width, new_height)
            else:
                return (width, height)
    return OnlyShrink

BoxFitWithRotationOnlyShrink = only_shrink(BoxFitWithRotation)
BoxFitConstrainOnlyShrink = only_shrink(BoxFitConstrain)

image_sizes = {
        'thumb75': BoxFitExpanded(75, 75),
        'iphone3': BoxFitWithRotationOnlyShrink(480, 320),
        'iphone4': BoxFitWithRotationOnlyShrink(960, 640),
        'iphone5': BoxFitWithRotationOnlyShrink(1136, 640),
        'crop140': BoxFitCrop(140, 140),
        '940x570': BoxFitConstrainOnlyShrink(940, 570)
        }

def process_uploaded_image(bucket, photo_id):
    location, directory = bucket.split(':')
    if location != 'local':
        raise ValueError('Unknown photo bucket location: ' + location)

    bucket_directory = os.path.join(settings.LOCAL_PHOTO_BUCKETS_BASE_PATH, directory)
    img_file_path = os.path.join(bucket_directory, photo_id + '.jpg')

    img = Image.open(img_file_path)
    (img_width, img_height) = (img.size[0], img.size[1])

    # TODO Optimization: If multiple image targets happen to have the same
    # dimensions then re-use the result, either by copying the file, or using a
    # symlink

    for image_size_str, image_dimensions_calculator in image_sizes.iteritems():
        (new_width, new_height) = image_dimensions_calculator.get_image_dimensions(img_width, img_height)
        new_img = ImageOps.fit(img, (new_width, new_height), Image.ANTIALIAS, 0, (0.5, 0.5))
        new_img.save(os.path.join(bucket_directory, photo_id + '_' + image_size_str + '.jpg'))

    return (img_width, img_height)

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
