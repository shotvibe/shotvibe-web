# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting field 'Photo.width'
        db.delete_column(u'photos_photo', 'width')

        # Deleting field 'Photo.height'
        db.delete_column(u'photos_photo', 'height')

        # Deleting field 'Photo.bucket'
        db.delete_column(u'photos_photo', 'bucket')

        # Adding field 'Photo.storage_id'
        db.add_column(u'photos_photo', 'storage_id',
                      self.gf('django.db.models.fields.CharField')(default='temporary-placeholder', max_length=128, db_index=True),
                      keep_default=False)

        # Adding field 'Photo.subdomain'
        db.add_column(u'photos_photo', 'subdomain',
                      self.gf('django.db.models.fields.CharField')(default='temporary-placeholder', max_length=64),
                      keep_default=False)

        # Deleting field 'PendingPhoto.bucket'
        db.delete_column(u'photos_pendingphoto', 'bucket')

        # Adding field 'PendingPhoto.storage_id'
        db.add_column(u'photos_pendingphoto', 'storage_id',
                      self.gf('django.db.models.fields.CharField')(default='', unique=True, max_length=128),
                      keep_default=False)

        # Adding field 'PendingPhoto.file_uploaded_time'
        db.add_column(u'photos_pendingphoto', 'file_uploaded_time',
                      self.gf('django.db.models.fields.DateTimeField')(null=True),
                      keep_default=False)

        # Adding field 'PendingPhoto.processing_done_time'
        db.add_column(u'photos_pendingphoto', 'processing_done_time',
                      self.gf('django.db.models.fields.DateTimeField')(null=True),
                      keep_default=False)


    def backwards(self, orm):

        # User chose to not deal with backwards NULL issues for 'Photo.width'
        raise RuntimeError("Cannot reverse this migration. 'Photo.width' and its values cannot be restored.")

        # The following code is provided here to aid in writing a correct migration        # Adding field 'Photo.width'
        db.add_column(u'photos_photo', 'width',
                      self.gf('django.db.models.fields.IntegerField')(),
                      keep_default=False)


        # User chose to not deal with backwards NULL issues for 'Photo.height'
        raise RuntimeError("Cannot reverse this migration. 'Photo.height' and its values cannot be restored.")

        # The following code is provided here to aid in writing a correct migration        # Adding field 'Photo.height'
        db.add_column(u'photos_photo', 'height',
                      self.gf('django.db.models.fields.IntegerField')(),
                      keep_default=False)


        # User chose to not deal with backwards NULL issues for 'Photo.bucket'
        raise RuntimeError("Cannot reverse this migration. 'Photo.bucket' and its values cannot be restored.")

        # The following code is provided here to aid in writing a correct migration        # Adding field 'Photo.bucket'
        db.add_column(u'photos_photo', 'bucket',
                      self.gf('django.db.models.fields.CharField')(max_length=64),
                      keep_default=False)

        # Deleting field 'Photo.storage_id'
        db.delete_column(u'photos_photo', 'storage_id')

        # Deleting field 'Photo.subdomain'
        db.delete_column(u'photos_photo', 'subdomain')

        # Adding field 'PendingPhoto.bucket'
        db.add_column(u'photos_pendingphoto', 'bucket',
                      self.gf('django.db.models.fields.CharField')(default='local:photos02', max_length=64),
                      keep_default=False)

        # Deleting field 'PendingPhoto.storage_id'
        db.delete_column(u'photos_pendingphoto', 'storage_id')

        # Deleting field 'PendingPhoto.file_uploaded_time'
        db.delete_column(u'photos_pendingphoto', 'file_uploaded_time')

        # Deleting field 'PendingPhoto.processing_done_time'
        db.delete_column(u'photos_pendingphoto', 'processing_done_time')


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
            'avatar_file': ('django.db.models.fields.CharField', [], {'default': "'s3:shotvibe-avatars-01:default-avatar-0046.jpg'", 'max_length': '128'}),
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Group']"}),
            'id': ('django.db.models.fields.IntegerField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_registered': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'nickname': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'primary_email': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'on_delete': 'models.SET_NULL', 'to': u"orm['phone_auth.UserEmail']", 'blank': 'True', 'null': 'True', 'db_index': 'False'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"})
        },
        u'phone_auth.useremail': {
            'Meta': {'object_name': 'UserEmail'},
            'email': ('django.db.models.fields.EmailField', [], {'unique': 'True', 'max_length': '75'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['phone_auth.User']"})
        },
        u'photos.album': {
            'Meta': {'object_name': 'Album'},
            'creator': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'to': u"orm['phone_auth.User']"}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_updated': ('django.db.models.fields.DateTimeField', [], {}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'revision_number': ('django.db.models.fields.IntegerField', [], {})
        },
        u'photos.albummember': {
            'Meta': {'unique_together': "(('user', 'album'),)", 'object_name': 'AlbumMember', 'db_table': "'photos_album_members'"},
            'added_by_user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'created_album_memberships'", 'to': u"orm['phone_auth.User']"}),
            'album': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'memberships'", 'to': u"orm['photos.Album']"}),
            'datetime_added': ('django.db.models.fields.DateTimeField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_access': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'album_membership'", 'to': u"orm['phone_auth.User']"})
        },
        u'photos.pendingphoto': {
            'Meta': {'object_name': 'PendingPhoto'},
            'author': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['phone_auth.User']"}),
            'file_uploaded_time': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'photo_id': ('django.db.models.fields.CharField', [], {'max_length': '128', 'primary_key': 'True'}),
            'processing_done_time': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'start_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'storage_id': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '128'})
        },
        u'photos.photo': {
            'Meta': {'ordering': "['album_index']", 'object_name': 'Photo'},
            'album': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['photos.Album']"}),
            'album_index': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'author': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['phone_auth.User']"}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            'photo_id': ('django.db.models.fields.CharField', [], {'max_length': '128', 'primary_key': 'True'}),
            'storage_id': ('django.db.models.fields.CharField', [], {'max_length': '128', 'db_index': 'True'}),
            'subdomain': ('django.db.models.fields.CharField', [], {'max_length': '64'})
        }
    }

    complete_apps = ['photos']
