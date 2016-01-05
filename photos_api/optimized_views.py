import collections

from django.db import connection

from phone_auth.models import User, avatar_url_from_avatar_file_data
from photos.models import Photo, Video, AlbumMember
from photos_api.serializers import album_name_or_members

def get_album_members_payload(album_id):
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT user_id0,
               user_nickname0,
               user_last_online0,
               user_avatar_file0,
               member_album_admin0,
               member_added_by_user_id0,
               user_phone_verified0,
               user_phone_link_visited0
        FROM (SELECT u.id as user_id0,
                     u.nickname as user_nickname0,
                     u.last_online as user_last_online0,
                     u.avatar_file as user_avatar_file0,
                     (SELECT COUNT(*)
                      FROM phone_auth_phonenumber
                      WHERE user_id=u.id AND
                            verified) as user_phone_verified0,
                     (SELECT COUNT(*)
                      FROM phone_auth_phonenumberlinkcode
                      LEFT OUTER JOIN phone_auth_phonenumber
                      ON phone_auth_phonenumberlinkcode.phone_number_id=phone_auth_phonenumber.id
                      WHERE phone_auth_phonenumber.user_id = u.id AND
                            phone_auth_phonenumberlinkcode.was_visited) as user_phone_link_visited0
              FROM phone_auth_user u) as T1,
             (SELECT user_id as user_id1,
                     album_admin as member_album_admin0,
                     added_by_user_id as member_added_by_user_id0
              FROM photos_album_members
              WHERE album_id=%s) as T2
        WHERE user_id0=user_id1
        """,
        [album_id])

    members = []
    for row in cursor.fetchall():
        (row_user_id,
        row_user_nickname,
        row_user_last_online,
        row_user_avatar_file,
        row_member_album_admin,
        row_member_added_by_user_id,
        row_user_phone_verified,
        row_user_phone_link_visited) = row

        if row_user_phone_verified > 0:
            invite_status = User.STATUS_JOINED
        elif row_user_phone_link_visited > 0:
            invite_status = User.STATUS_INVITATION_VIEWED
        else:
            invite_status = User.STATUS_SMS_SENT

        members.append({
            'id': row_user_id,
            'nickname': row_user_nickname,
            'last_online': row_user_last_online,
            'avatar_url': avatar_url_from_avatar_file_data(row_user_avatar_file),
            'album_admin': row_member_album_admin,
            'added_by_user_id': row_member_added_by_user_id,
            'invite_status': invite_status
        })

    return members

def get_album_photos_payload(user_id, album_id, only_newest=None):
    if only_newest:
        order_limit_clause = \
           """
           ORDER BY album_index0 DESC
           LIMIT {0}
           """.format(only_newest)
    else:
        order_limit_clause = \
           """
           ORDER BY album_index0
           """

    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT photo_id0,
               photo_media_type0,
               photo_client_upload_id0,
               photo_subdomain0,
               photo_date_created0,
               video_status0,
               video_storage_id0,
               video_duration0,
               photo_global_glance_score0,
               photo_my_glance_score0,
               author_id0,
               author_nickname0,
               author_last_online0,
               author_avatar_file0
        FROM (SELECT p.photo_id as photo_id0,
                     p.media_type as photo_media_type0,
                     p.client_upload_id as photo_client_upload_id0,
                     p.subdomain as photo_subdomain0,
                     p.date_created as photo_date_created0,
                     p.album_id as album_id0,
                     p.album_index as album_index0,
                     photos_video.status as video_status0,
                     photos_video.storage_id as video_storage_id0,
                     photos_video.duration as video_duration0,
                     phone_auth_user.id as author_id0,
                     phone_auth_user.nickname as author_nickname0,
                     phone_auth_user.last_online as author_last_online0,
                     phone_auth_user.avatar_file as author_avatar_file0,
                     (CASE WHEN p.copied_from_photo_id IS NULL
                           THEN (SELECT COALESCE(SUM(photo_glance_score), 0) + p.photo_glance_score
                                 FROM photos_photo
                                 WHERE copied_from_photo_id=p.photo_id)
                           ELSE (SELECT COALESCE(SUM(photo_glance_score), 0) +
                                            (SELECT photo_glance_score
                                             FROM photos_photo
                                             WHERE photo_id=p.copied_from_photo_id)
                                 FROM photos_photo
                                 WHERE copied_from_photo_id=p.copied_from_photo_id)
                           END) as photo_global_glance_score0,
                     (SELECT score_delta
                      FROM photos_photoglancescoredelta
                      WHERE photo_id=p.photo_id AND
                            author_id=%s) as photo_my_glance_score0
              FROM photos_photo p
              LEFT OUTER JOIN phone_auth_user
              ON p.author_id=phone_auth_user.id
              LEFT OUTER JOIN photos_video
              ON p.storage_id=photos_video.storage_id) as T1
        WHERE album_id0=%s
        """ + order_limit_clause,
        [user_id, album_id])

    photos = collections.OrderedDict()
    for row in cursor.fetchall():
        (row_photo_id,
        row_media_type,
        row_client_upload_id,
        row_photo_subdomain,
        row_photo_date_created,
        row_video_status,
        row_video_storage_id,
        row_video_duration,
        row_photo_global_glance_score,
        row_photo_my_glance_score,
        row_author_id,
        row_author_nickname,
        row_author_last_online,
        row_author_avatar_file) = row

        if row_photo_my_glance_score:
            my_glance_score_delta = row_photo_my_glance_score
        else:
            my_glance_score_delta = 0

        # Manually create a Photo instance so we can use it's helper methods
        photo = Photo(photo_id=row_photo_id, subdomain=row_photo_subdomain, media_type=row_media_type)

        photos[row_photo_id] = {
            'photo_id': row_photo_id,
            'media_type': photo.get_media_type_display(),
            'client_upload_id': row_client_upload_id,
            'photo_url': photo.get_photo_url(),
            'date_created': row_photo_date_created,
            'author': {
                'id': row_author_id,
                'nickname': row_author_nickname,
                'last_online': row_author_last_online,
                'avatar_url': avatar_url_from_avatar_file_data(row_author_avatar_file)
            },
            'comments': [], # Will be filled in later
            'user_tags': [], # Not used yet, will be left empty
            'glances': [], # Deprecated, will be left empty
            'global_glance_score': row_photo_global_glance_score,
            'my_glance_score_delta': my_glance_score_delta
        }
        if photo.is_video():
            # Manually create a Video instance so we can use it's helper methods
            video = Video(status=row_video_status)
            photos[row_photo_id]['video_status'] = video.get_status_display()
            photos[row_photo_id]['video_url'] = Video.get_video_url(row_video_storage_id)
            photos[row_photo_id]['video_thumbnail_url'] = Video.get_video_thumbnail_url(row_video_storage_id)
            photos[row_photo_id]['video_duration'] = row_video_duration

    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT photos_photo.photo_id,
               phone_auth_user.id,
               phone_auth_user.nickname,
               phone_auth_user.last_online,
               phone_auth_user.avatar_file,
               photos_photocomment.date_created,
               photos_photocomment.client_msg_id,
               photos_photocomment.comment_text
        FROM photos_photocomment
        LEFT OUTER JOIN photos_photo
            ON photos_photocomment.photo_id=photos_photo.photo_id
        LEFT OUTER JOIN phone_auth_user
            ON photos_photocomment.author_id=phone_auth_user.id
        WHERE album_id=%s
        ORDER BY photos_photocomment.date_created;
        """,
        [album_id])

    for row in cursor.fetchall():
        (row_photo_id,
        row_photo_author_user_id,
        row_photo_author_user_nickname,
        row_photo_author_user_last_online,
        row_photo_author_user_avatar_file,
        row_photocomment_date_created,
        row_photocomment_client_msg_id,
        row_photocomment_comment_text) = row

        photo_id = row_photo_id
        try:
            photos[photo_id]['comments'].append({
                'author': {
                    'id': row_photo_author_user_id,
                    'nickname': row_photo_author_user_nickname,
                    'last_online': row_photo_author_user_last_online,
                    'avatar_url': avatar_url_from_avatar_file_data(row_photo_author_user_avatar_file),
                },
                'date_created': row_photocomment_date_created,
                'client_msg_id': row_photocomment_client_msg_id,
                'comment': row_photocomment_comment_text,
            })
        except KeyError:
            # Ignore comments on photos that we are not interested in
            pass

    return photos.values()

def get_album_detail_payload(user, album):
    album_member = AlbumMember.objects.filter(user=user, album=album).first()

    members = get_album_members_payload(album.id)

    photos = get_album_photos_payload(user.id, album.id)

    creator = {
        'id': album.creator.id,
        'nickname': album.creator.nickname,
        'last_online': album.creator.last_online,
        'avatar_url': album.creator.get_avatar_url()
    }

    if album_member:
        name = album_name_or_members(album_member)
        last_access = album_member.last_access
        num_new_photos = album_member.get_num_new_photos()
    else:
        name = album.name
        last_access = None
        num_new_photos = 0

    payload = {
        'id': album.id,
        'name': name,
        'creator': creator,
        'date_created': album.date_created,
        'last_updated': album.last_updated,
        'last_access': last_access,
        'num_new_photos': num_new_photos,
        'members': members,
        'photos': photos
    }
    return payload


def get_album_list_payload(user_id):
    if connection.vendor == 'sqlite':
        am_last_access_offset = \
            """
            datetime(am.last_access, '0.1 second')
            """
    else:
        am_last_access_offset = \
            """
            (am.last_access + INTERVAL '0.001 second')
            """

    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT album_id0,
               album_name0,
               album_date_created0,
               album_last_updated0,
               album_revision_number0,
               album_last_access0,
               album_num_new_photos0,
               album_creator_id0,
               album_creator_nickname0,
               album_creator_last_online0,
               album_creator_avatar_file0
        FROM (SELECT am.album_id as album_id0,
                     am.last_access as album_last_access0,
                     (CASE WHEN am.last_access IS NULL
                           THEN (SELECT COUNT(*)
                                 FROM photos_photo
                                 WHERE photos_photo.album_id = am.album_id AND
                                       photos_photo.author_id != %s)
                           ELSE (SELECT COUNT(*)
                                 FROM photos_photo
                                 WHERE photos_photo.album_id = am.album_id AND
                                       photos_photo.author_id != %s AND
                                       photos_photo.date_created > """ + am_last_access_offset + """)
                           END) as album_num_new_photos0
              FROM photos_album_members am
              WHERE am.user_id = %s) as T1,
             (SELECT a.id as album_id1,
                     a.name as album_name0,
                     a.date_created as album_date_created0,
                     a.last_updated as album_last_updated0,
                     a.revision_number as album_revision_number0,
                     a.creator_id as album_creator_id0,
                     phone_auth_user.nickname as album_creator_nickname0,
                     phone_auth_user.last_online as album_creator_last_online0,
                     phone_auth_user.avatar_file as album_creator_avatar_file0
              FROM photos_album a
              LEFT OUTER JOIN phone_auth_user
              ON a.creator_id = phone_auth_user.id) as T2
        WHERE album_id0 = album_id1
        """,
        [user_id, user_id, user_id])

    albums = collections.OrderedDict()
    for row in cursor.fetchall():
        (row_album_id,
        row_album_name,
        row_album_date_created,
        row_album_last_updated,
        row_album_revision_number,
        row_album_last_access,
        row_album_num_new_photos,
        row_album_creator_id,
        row_album_creator_nickname,
        row_album_creator_last_online,
        row_album_creator_avatar_file) = row

        albums[row_album_id] = {
            'id': row_album_id,

            # TODO Could be optimized. Instead of a seperate query for each album, do
            # one big query of all the members of all the albums:
            'name': album_name_or_members(AlbumMember.objects.get(user__id=user_id, album__id=row_album_id)),

            'creator': {
                'id': row_album_creator_id,
                'nickname': row_album_creator_nickname,
                'last_online': row_album_creator_last_online,
                'avatar_url': avatar_url_from_avatar_file_data(row_album_creator_avatar_file)
            },
            'date_created': row_album_date_created,
            'last_updated': row_album_last_updated,
            'etag': u'{0}'.format(row_album_revision_number), # See: photos.models.Album.get_etag

            # TODO: This is not optimized, we should do a single SQL query to
            # get all photos of all albums, instead of a separate query per
            # album:
            'latest_photos': get_album_photos_payload(user_id, row_album_id, only_newest=2),

            'num_new_photos': row_album_num_new_photos,
            'last_access': row_album_last_access
        }

    return albums.values()
