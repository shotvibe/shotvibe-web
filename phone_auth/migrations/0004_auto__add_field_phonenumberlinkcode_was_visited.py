# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'PhoneNumberLinkCode.was_visited'
        db.add_column(u'phone_auth_phonenumberlinkcode', 'was_visited',
                      self.gf('django.db.models.fields.BooleanField')(default=False),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'PhoneNumberLinkCode.was_visited'
        db.delete_column(u'phone_auth_phonenumberlinkcode', 'was_visited')


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
        u'phone_auth.anonymousphonenumber': {
            'Meta': {'object_name': 'AnonymousPhoneNumber'},
            'avatar_file': ('django.db.models.fields.CharField', [], {'default': "'s3:shotvibe-avatars-01:default-avatar-0024.jpg'", 'max_length': '128'}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_mobile': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_mobile_queried': ('django.db.models.fields.DateTimeField', [], {}),
            'phone_number': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '32', 'db_index': 'True'})
        },
        u'phone_auth.authtoken': {
            'Meta': {'object_name': 'AuthToken'},
            'date_created': ('django.db.models.fields.DateTimeField', [], {}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'key': ('django.db.models.fields.CharField', [], {'max_length': '40', 'primary_key': 'True'}),
            'last_access': ('django.db.models.fields.DateTimeField', [], {}),
            'last_access_ip': ('django.db.models.fields.GenericIPAddressField', [], {'max_length': '39', 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['phone_auth.User']"})
        },
        u'phone_auth.phonecontact': {
            'Meta': {'object_name': 'PhoneContact'},
            'anonymous_phone_number': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['phone_auth.AnonymousPhoneNumber']"}),
            'contact_nickname': ('django.db.models.fields.TextField', [], {}),
            'created_by_user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'created_phone_contacts'", 'to': u"orm['phone_auth.User']"}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'related_name': "'phone_contacts'", 'null': 'True', 'blank': 'True', 'to': u"orm['phone_auth.User']"})
        },
        u'phone_auth.phonenumber': {
            'Meta': {'object_name': 'PhoneNumber'},
            'date_created': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'phone_number': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '32'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['phone_auth.User']"}),
            'verified': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        u'phone_auth.phonenumberconfirmsmscode': {
            'Meta': {'object_name': 'PhoneNumberConfirmSMSCode'},
            'confirmation_code': ('django.db.models.fields.CharField', [], {'max_length': '6'}),
            'confirmation_key': ('django.db.models.fields.CharField', [], {'max_length': '40', 'primary_key': 'True'}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            'phone_number': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['phone_auth.PhoneNumber']"})
        },
        u'phone_auth.phonenumberlinkcode': {
            'Meta': {'object_name': 'PhoneNumberLinkCode'},
            'date_created': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            'invite_code': ('django.db.models.fields.CharField', [], {'max_length': '32', 'primary_key': 'True'}),
            'inviting_user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'to': u"orm['phone_auth.User']"}),
            'phone_number': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['phone_auth.PhoneNumber']", 'unique': 'True'}),
            'was_visited': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        u'phone_auth.user': {
            'Meta': {'object_name': 'User'},
            'avatar_file': ('django.db.models.fields.CharField', [], {'default': "'s3:shotvibe-avatars-01:default-avatar-0071.jpg'", 'max_length': '128'}),
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
        }
    }

    complete_apps = ['phone_auth']
