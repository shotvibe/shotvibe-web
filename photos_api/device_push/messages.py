class Message(object):
    def format_upp_msg(self, user_ids):
        return {
                'user_ids': [unicode(id) for id in user_ids]
                'gcm': {
                    'data': {
                        'type': type_name
                        }
                    }
                }

    def get_sound(self):
        """
        Default is no sound
        """
        return None

class PhotosAdded(Message):
    type_name = 'photos_added'

    def __init__(self, album_id, author_id, album_name, author_name, num_photos):
        self.album_id = album_id
        self.author_id = author_id
        self.album_name = album_name
        self.author_name = author_name
        self.num_photos = num_photos

    def get_payload(self):
        return {
                'album_id': self.album_id,
                'author': self.author_name,
                'album_name': self.album_name,
                'num_photos': self.num_photos
                }

    def get_sound(self):
        pass
