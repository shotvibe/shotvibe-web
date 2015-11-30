import collections

from django.db import connection

from phone_auth.models import User, avatar_url_from_avatar_file_data
from photos.models import Photo, AlbumMember
from photos_api.serializers import album_name_or_members

def get_album_members_payload(album_id):
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT user_id0,
               user_nickname0,
               user_avatar_file0,
               member_album_admin0,
               member_added_by_user_id0,
               user_phone_verified0,
               user_phone_link_visited0
        FROM (SELECT u.id as user_id0,
                     u.nickname as user_nickname0,
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
        if row[5] > 0:
            invite_status = User.STATUS_JOINED
        elif row[6] > 0:
            invite_status = User.STATUS_INVITATION_VIEWED
        else:
            invite_status = User.STATUS_SMS_SENT

        members.append({
            'id': row[0],
            'nickname': row[1],
            'avatar_url': avatar_url_from_avatar_file_data(row[2]),
            'album_admin': row[3],
            'added_by_user_id': row[4],
            'invite_status': invite_status
        })

    return members

def get_album_photos_payload(user_id, album_id):
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT photo_id0,
               photo_subdomain0,
               photo_date_created0,
               photo_global_glance_score0,
               photo_my_glance_score0,
               author_id0,
               author_nickname0,
               author_avatar_file0
        FROM (SELECT p.photo_id as photo_id0,
                     p.subdomain as photo_subdomain0,
                     p.date_created as photo_date_created0,
                     p.album_id as album_id0,
                     p.album_index as album_index0,
                     phone_auth_user.id as author_id0,
                     phone_auth_user.nickname as author_nickname0,
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
              ON p.author_id=phone_auth_user.id) as T1
        WHERE album_id0=%s
        ORDER BY album_index0
        """,
        [user_id, album_id])

    photos = collections.OrderedDict()
    for row in cursor.fetchall():
        (row_photo_id,
        row_photo_subdomain,
        row_photo_date_created,
        row_photo_global_glance_score,
        row_photo_my_glance_score,
        row_author_id,
        row_author_nickname,
        row_author_avatar_file) = row

        if row_photo_my_glance_score:
            my_glance_score_delta = row_photo_my_glance_score
        else:
            my_glance_score_delta = 0

        # Manually create a Photo instance so we can use it's helper methods
        photo = Photo(photo_id=row_photo_id, subdomain=row_photo_subdomain)

        photos[row_photo_id] = {
            'photo_id': row_photo_id,
            'photo_url': photo.get_photo_url(),
            'date_created': row_photo_date_created,
            'author': {
                'id': row_author_id,
                'nickname': row_author_nickname,
                'avatar_url': avatar_url_from_avatar_file_data(row_author_avatar_file)
            },
            'comments': [], # Will be filled in later
            'user_tags': [], # Not used yet, will be left empty
            'glances': [], # Deprecated, will be left empty
            'global_glance_score': row_photo_global_glance_score,
            'my_glance_score_delta': my_glance_score_delta
        }

    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT photos_photo.photo_id,
               phone_auth_user.id,
               phone_auth_user.nickname,
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
        photo_id = row[0]
        photos[photo_id]['comments'].append({
            'author': {
                'id': row[1],
                'nickname': row[2],
                'avatar_url': avatar_url_from_avatar_file_data(row[3]),
            },
            'date_created': row[4],
            'client_msg_id': row[5],
            'comment': row[6],
        })

    return photos.values()

def get_album_detail_payload(user, album):
    album_member = AlbumMember.objects.filter(user=user, album=album).first()

    members = get_album_members_payload(album.id)

    photos = get_album_photos_payload(user.id, album.id)

    creator = {
        'id': album.creator.id,
        'nickname': album.creator.nickname,
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
