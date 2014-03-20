# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Organization'
        db.create_table(u'affiliates_organization', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('code', self.gf('django.db.models.fields.CharField')(max_length=128)),
        ))
        db.send_create_signal(u'affiliates', ['Organization'])

        # Adding model 'OrganizationUser'
        db.create_table(u'affiliates_organizationuser', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('organization', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['affiliates.Organization'])),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['phone_auth.User'])),
        ))
        db.send_create_signal(u'affiliates', ['OrganizationUser'])

        # Adding unique constraint on 'OrganizationUser', fields ['organization', 'user']
        db.create_unique(u'affiliates_organizationuser', ['organization_id', 'user_id'])

        # Adding model 'Event'
        db.create_table(u'affiliates_event', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('organization', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['affiliates.Organization'])),
            ('created_by', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['phone_auth.User'])),
            ('album', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['photos.Album'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('time', self.gf('django.db.models.fields.DateTimeField')()),
            ('sms_message', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('push_notification', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('location', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('html_content', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal(u'affiliates', ['Event'])

        # Adding model 'EventInvite'
        db.create_table(u'affiliates_eventinvite', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('event', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['affiliates.Event'])),
            ('nickname', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('phone_number', self.gf('django.db.models.fields.CharField')(max_length=32)),
        ))
        db.send_create_signal(u'affiliates', ['EventInvite'])

        # Adding unique constraint on 'EventInvite', fields ['event', 'phone_number']
        db.create_unique(u'affiliates_eventinvite', ['event_id', 'phone_number'])

        # Adding model 'EventLink'
        db.create_table(u'affiliates_eventlink', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('slug', self.gf('django.db.models.fields.CharField')(max_length=255, unique=True, null=True, blank=True)),
            ('event', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['affiliates.Event'], null=True)),
            ('invite', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['affiliates.EventInvite'], unique=True, null=True)),
            ('time_sent', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('visited_count', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('downloaded_count', self.gf('django.db.models.fields.IntegerField')(default=0)),
        ))
        db.send_create_signal(u'affiliates', ['EventLink'])


    def backwards(self, orm):
        # Removing unique constraint on 'EventInvite', fields ['event', 'phone_number']
        db.delete_unique(u'affiliates_eventinvite', ['event_id', 'phone_number'])

        # Removing unique constraint on 'OrganizationUser', fields ['organization', 'user']
        db.delete_unique(u'affiliates_organizationuser', ['organization_id', 'user_id'])

        # Deleting model 'Organization'
        db.delete_table(u'affiliates_organization')

        # Deleting model 'OrganizationUser'
        db.delete_table(u'affiliates_organizationuser')

        # Deleting model 'Event'
        db.delete_table(u'affiliates_event')

        # Deleting model 'EventInvite'
        db.delete_table(u'affiliates_eventinvite')

        # Deleting model 'EventLink'
        db.delete_table(u'affiliates_eventlink')


    models = {
        u'affiliates.event': {
            'Meta': {'object_name': 'Event'},
            'album': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['photos.Album']"}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['phone_auth.User']"}),
            'html_content': ('django.db.models.fields.TextField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'location': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'organization': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['affiliates.Organization']"}),
            'push_notification': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'sms_message': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'time': ('django.db.models.fields.DateTimeField', [], {})
        },
        u'affiliates.eventinvite': {
            'Meta': {'unique_together': "(('event', 'phone_number'),)", 'object_name': 'EventInvite'},
            'event': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['affiliates.Event']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'nickname': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'phone_number': ('django.db.models.fields.CharField', [], {'max_length': '32'})
        },
        u'affiliates.eventlink': {
            'Meta': {'object_name': 'EventLink'},
            'downloaded_count': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'event': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['affiliates.Event']", 'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invite': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['affiliates.EventInvite']", 'unique': 'True', 'null': 'True'}),
            'slug': ('django.db.models.fields.CharField', [], {'max_length': '255', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'time_sent': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'visited_count': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        u'affiliates.organization': {
            'Meta': {'object_name': 'Organization'},
            'code': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        u'affiliates.organizationuser': {
            'Meta': {'unique_together': "(('organization', 'user'),)", 'object_name': 'OrganizationUser'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'organization': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['affiliates.Organization']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['phone_auth.User']"})
        },
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
            'avatar_file': ('django.db.models.fields.CharField', [], {'default': "'s3:shotvibe-avatars-01:default-avatar-0071.jpg'", 'max_length': '128'}),
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
        }
    }

    complete_apps = ['affiliates']
