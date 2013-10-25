from django.dispatch import Signal

album_created = Signal(providing_args=['album'])

photos_added_to_album = Signal(providing_args=['photos', 'by_user', 'to_album'])

photos_removed_from_album = Signal(providing_args=['photos', 'by_user', 'from_album'])

members_added_to_album = Signal(providing_args=['member_users', 'by_user',
                                                'to_album'])

member_leave_album = Signal(providing_args=['user', 'album'])
