from photos.models import AlbumMember
from photos_api import device_push
from photos_api import signals


def send_push_on_photos_added_to_album(sender, **kwargs):
    """When new photos added to the album then send push notifications
    to all album members"""

    photos = kwargs.get('photos')
    user = kwargs.get('by_user')
    album = kwargs.get('to_album')

    # Send push notifications to the album members about just added photos
    membership_query = AlbumMember.objects.filter(album=album).only('user__id', 'album_name')

    for member in membership_query:
        device_push.broadcast_photos_added_to_album(
            album_id=album.id,
            author_id=user.id,
            album_name=member.album_name,
            author_name=user.nickname,
            num_photos=len(photos),
            user_ids=[member.user.id])

    # #70 3)
    device_push.broadcast_album_sync(user.id, album.id)

signals.photos_added_to_album.connect(send_push_on_photos_added_to_album)


def send_push_on_photo_removed_from_album(sender, **kwargs):
    photos = kwargs.get('photos')
    user = kwargs.get('by_user')
    album = kwargs.get('from_album')

    users = album.get_member_users()
    user_ids = [user.id for user in users]

    # #70 3)
    device_push.broadcast_album_sync(user_ids, album.id)

signals.photos_removed_from_album.connect(send_push_on_photo_removed_from_album)

def send_push_on_album_created(sender, **kwargs):
    album = kwargs.get('album')
    # Send push notifications
    # ====================================================
    # https://github.com/shotvibe/shotvibe-web/issues/70
    # Do not send push notification to user himself.
    # --------
    # device_push.broadcast_members_added_to_album(album.id,
    #                                              album.name,
    #                                              album.creator.nickname,
    #                                              [album.creator.id])
    device_push.broadcast_album_list_sync([album.creator.id])

signals.album_created.connect(send_push_on_album_created)


def send_push_on_members_added_to_album(sender, **kwargs):

    member_users = kwargs.get('member_users')
    user = kwargs.get('by_user')
    album = kwargs.get('to_album')

    # Send push notification
    device_push.broadcast_members_added_to_album(album.id,
                                                 album.get_name(),
                                                 user.nickname,
                                                 [nu.id for nu in member_users])

signals.members_added_to_album.connect(send_push_on_members_added_to_album)


def send_push_on_user_leave_album(sender, **kwargs):
    user = kwargs.get('user')
    # Send push notification to the user.
    device_push.broadcast_album_list_sync(user.id)

signals.member_leave_album.connect(send_push_on_user_leave_album)
