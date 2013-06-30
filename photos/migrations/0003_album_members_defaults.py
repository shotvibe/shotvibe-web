# -*- coding: utf-8 -*-
import datetime
from django.utils import timezone
from south.db import db
from south.v2 import DataMigration


class Migration(DataMigration):

    def forwards(self, orm):
        # Set default values for AlbumMember.added_by_member and AlbumMember.datetime_added. It only applies to
        # the existing records.
        for membership in orm.AlbumMember.objects.all():
            # Set added_by_member to the creator of the album
            album_creator = membership.album.creator

            if album_creator != membership.user:
                creator_membership = orm.AlbumMember.objects.get(album=membership.album, user=album_creator)
                membership.added_by_member = creator_membership

            # Set `datetime_added` to the datetime when album was created by default
            membership.datetime_added = membership.album.date_created

            membership.save()

    def backwards(self, orm):
        "Write your backwards methods here."
        # raise RuntimeError("Cannot reverse this migration.")
        for membership in orm.AlbumMember.objects.all():

            # Set added_by_member to 0
            membership.added_by_member = 0

            # Set `datetime_added` to the current datetime
            membership.datetime_added = timezone.now()

            membership.save()

    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'phone_auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.IntegerField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_registered': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'nickname': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'primary_email': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'on_delete': 'models.SET_NULL', 'to': u"orm['phone_auth.UserEmail']", 'blank': 'True', 'null': 'True', 'db_index': 'False'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'phone_auth.useremail': {
            'Meta': {'object_name': 'UserEmail'},
            'email': ('django.db.models.fields.EmailField', [], {'unique': 'True', 'max_length': '75'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['phone_auth.User']"})
        },
        u'photos.album': {
            'Meta': {'object_name': 'Album'},
            'creator': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'created_albums'", 'to': u"orm['phone_auth.User']"}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_updated': ('django.db.models.fields.DateTimeField', [], {}),
            'members': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['phone_auth.User']", 'through': u"orm['photos.AlbumMember']", 'symmetrical': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'revision_number': ('django.db.models.fields.IntegerField', [], {})
        },
        u'photos.albummember': {
            'Meta': {'unique_together': "(('user', 'album'),)", 'object_name': 'AlbumMember', 'db_table': "'photos_album_members'"},
            'added_by_member': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'created_album_memberships'", 'to': u"orm['photos.AlbumMember']"}),
            'album': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['photos.Album']"}),
            'datetime_added': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'album_membership'", 'to': u"orm['phone_auth.User']"})
        },
        u'photos.pendingphoto': {
            'Meta': {'object_name': 'PendingPhoto'},
            'author': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['phone_auth.User']"}),
            'bucket': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'photo_id': ('django.db.models.fields.CharField', [], {'max_length': '128', 'primary_key': 'True'}),
            'start_time': ('django.db.models.fields.DateTimeField', [], {})
        },
        u'photos.photo': {
            'Meta': {'object_name': 'Photo'},
            'album': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['photos.Album']"}),
            'author': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['phone_auth.User']"}),
            'bucket': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            'height': ('django.db.models.fields.IntegerField', [], {}),
            'photo_id': ('django.db.models.fields.CharField', [], {'max_length': '128', 'primary_key': 'True'}),
            'width': ('django.db.models.fields.IntegerField', [], {})
        }
    }

    complete_apps = ['photos']
    symmetrical = True
