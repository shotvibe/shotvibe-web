import abc
from PIL import ExifTags
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
        'r_qvga' : BoxFitWithRotationOnlyShrink(320, 240),
        'r_hvga' : BoxFitWithRotationOnlyShrink(480, 320),
        'r_vga'  : BoxFitWithRotationOnlyShrink(640, 480),
        'r_wvga' : BoxFitWithRotationOnlyShrink(800, 480),
        'r_qhd'  : BoxFitWithRotationOnlyShrink(960, 540),
        'r_dvga' : BoxFitWithRotationOnlyShrink(960, 640),
        'r_dvgax': BoxFitWithRotationOnlyShrink(1136, 640),
        'r_hd'   : BoxFitWithRotationOnlyShrink(1280, 720),
        'r_xga'  : BoxFitWithRotationOnlyShrink(1024, 768),
        'r_wxga' : BoxFitWithRotationOnlyShrink(1280, 800),
        'r_fhd'  : BoxFitWithRotationOnlyShrink(1920, 1080),
        'r_qxga' : BoxFitWithRotationOnlyShrink(2048, 1536),
        'r_wqxga': BoxFitWithRotationOnlyShrink(2560, 1600),
        'thumb75': BoxFitExpanded(192, 192), # Name should be changed, and apps should be updated with the new name
        'iphone3': BoxFitWithRotationOnlyShrink(480, 320), # TODO Delete: Deprecated by r_hvgq
        'iphone4': BoxFitWithRotationOnlyShrink(960, 640), # TODO Delete: Deprecated by r_dvga
        'iphone5': BoxFitWithRotationOnlyShrink(1136, 640), # TODO Delete: Deprecated by r_dvgax
        'crop140': BoxFitCrop(140, 140),
        '940x570': BoxFitConstrainOnlyShrink(940, 570)
        }

def photo_is_processed(storage_id):
    # Check that the original file exists
    img_file_path = os.path.join(settings.LOCAL_PHOTOS_DIRECTORY, storage_id + '.jpg')
    if not os.path.isfile(img_file_path):
        return False

    # Check that all the processed resized images exist
    for image_size_str in image_sizes.iterkeys():
        resized_img_file_path = os.path.join(settings.LOCAL_PHOTOS_DIRECTORY, storage_id + '_' + image_size_str + '.jpg')
        if not os.path.isfile(resized_img_file_path):
            return False

    return True

"""
Takes into account EXIF Orientation metadata
"""
def load_image_correct_orientation(img_file_path):
    # Values for the "Orientation" tag from the EXIF Standard
    # See <http://www.sno.phy.queensu.ca/~phil/exiftool/TagNames/EXIF.html>
    EXIF_ORIENTATION_DEGREES = {
            3 : 180, # Rotated 180
            6 : 270, # Rotated 90 CW
            8 : 90 } # Rotated 90 CCW

    # Helper function
    def get_tag_value(exif, tag_name):
        if not exif:
            return None

        for tag, value in exif.items():
            decoded = ExifTags.TAGS.get(tag, tag)
            if decoded == tag_name:
                return value

        return None

    # Actual execution starts here:
    img = Image.open(img_file_path)
    if hasattr(img, '_getexif'):
        orientation_value = get_tag_value(img._getexif(), 'Orientation')
    else:
        orientation_value = None
    degrees = EXIF_ORIENTATION_DEGREES.get(orientation_value)
    if not (degrees is None):
        return img.rotate(degrees)
    else:
        return img

def create_mipmaps(img):
    (img_width, img_height) = (img.size[0], img.size[1])
    def calc_min_dimensions():
        target_sizes = [d.get_image_dimensions(img_width, img_height) for d in image_sizes.itervalues()]

        min_width = 9999999
        min_height = 9999999
        for w,h in target_sizes:
            if w < min_width:
                min_width = w
            if h < min_height:
                min_height = h
        return (min_width, min_height)

    min_width, min_height = calc_min_dimensions()

    w = img_width
    h = img_height

    mipmaps = [((w, h), img)]

    while w >= min_width*2 and h >= min_height*2:
        w //= 2
        h //= 2

        m = mipmaps[-1][1].resize((w, h), Image.BILINEAR)
        mipmaps.append(((w, h), m))

    mipmaps.reverse()
    return mipmaps

def get_best_mipmap(mipmaps, width, height):
    for ((w, h), m) in mipmaps:
        if w >= width and h >= height:
            return m
    # No matches found, return the largest mipmap (will be the original image):
    return mipmaps[-1][1]

def process_uploaded_image(storage_id):
    img_file_path = os.path.join(settings.LOCAL_PHOTOS_DIRECTORY, storage_id + '.jpg')

    img = load_image_correct_orientation(img_file_path)
    (img_width, img_height) = (img.size[0], img.size[1])

    mipmaps = create_mipmaps(img)

    saved_images = []

    def get_matching_saved_image(width, height):
        for (w, h), filename in saved_images:
            if w == new_width and h == new_height:
                return filename
        return None

    for image_size_str, image_dimensions_calculator in image_sizes.iteritems():
        (new_width, new_height) = image_dimensions_calculator.get_image_dimensions(img_width, img_height)

        filename = storage_id + '_' + image_size_str + '.jpg'

        saved_image = get_matching_saved_image(new_width, new_height)
        if saved_image:
            symlink_name = os.path.join(settings.LOCAL_PHOTOS_DIRECTORY, filename)
            if os.path.isfile(symlink_name):
                os.remove(symlink_name)
            os.symlink(saved_image, symlink_name)
            continue

        mipmap = get_best_mipmap(mipmaps, new_width, new_height)
        if new_width == mipmap.size[0] and new_height == mipmap.size[1]:
            new_img = mipmap
        elif new_height * img_width // img_height == new_width or new_width * img_height // img_width == new_height:
            new_img = mipmap.resize((new_width, new_height), Image.BILINEAR)
        else:
            new_img = ImageOps.fit(mipmap, (new_width, new_height), Image.BILINEAR, 0, (0.5, 0.5))
        new_img.save(os.path.join(settings.LOCAL_PHOTOS_DIRECTORY, filename))
        saved_images.append(((new_width, new_height), filename))

    return (img_width, img_height)

def process_file_upload(pending_photo, chunks):
    mkdir_p(settings.LOCAL_PHOTOS_DIRECTORY)
    save_file_path = os.path.join(settings.LOCAL_PHOTOS_DIRECTORY, pending_photo.storage_id + '.jpg')

    with open(save_file_path, 'wb') as f:
        for chunk in chunks:
            f.write(chunk)

    # TODO verify image

    process_uploaded_image(pending_photo.storage_id)

    pending_photo.set_uploaded()

# Taken from <http://stackoverflow.com/a/600612>
def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc: # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else: raise
