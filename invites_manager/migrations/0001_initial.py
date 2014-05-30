# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    depends_on = (
        ('phone_auth', '0004_auto__add_field_phonenumberlinkcode_was_visited'),
    )

    def forwards(self, orm):
        # Adding model 'SMSInviteMessage'
        db.create_table(u'invites_manager_smsinvitemessage', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('country_calling_code', self.gf('django.db.models.fields.PositiveSmallIntegerField')()),
            ('message_template', self.gf('django.db.models.fields.TextField')()),
            ('time_delay_hours', self.gf('django.db.models.fields.PositiveIntegerField')()),
        ))
        db.send_create_signal(u'invites_manager', ['SMSInviteMessage'])

        # Adding unique constraint on 'SMSInviteMessage', fields ['country_calling_code', 'time_delay_hours']
        db.create_unique(u'invites_manager_smsinvitemessage', ['country_calling_code', 'time_delay_hours'])

        # Adding model 'ScheduledSMSInviteMessage'
        db.create_table(u'invites_manager_scheduledsmsinvitemessage', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('invite_sent_time', self.gf('django.db.models.fields.DateTimeField')()),
            ('scheduled_delivery_time', self.gf('django.db.models.fields.DateTimeField')(db_index=True)),
            ('link_code', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['phone_auth.PhoneNumberLinkCode'])),
            ('message_template', self.gf('django.db.models.fields.TextField')()),
            ('time_delay_hours', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('sms_sender_phone_override', self.gf('django.db.models.fields.CharField')(max_length=32, null=True, blank=True)),
        ))
        db.send_create_signal(u'invites_manager', ['ScheduledSMSInviteMessage'])


    def backwards(self, orm):
        # Removing unique constraint on 'SMSInviteMessage', fields ['country_calling_code', 'time_delay_hours']
        db.delete_unique(u'invites_manager_smsinvitemessage', ['country_calling_code', 'time_delay_hours'])

        # Deleting model 'SMSInviteMessage'
        db.delete_table(u'invites_manager_smsinvitemessage')

        # Deleting model 'ScheduledSMSInviteMessage'
        db.delete_table(u'invites_manager_scheduledsmsinvitemessage')


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
        u'invites_manager.scheduledsmsinvitemessage': {
            'Meta': {'object_name': 'ScheduledSMSInviteMessage'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invite_sent_time': ('django.db.models.fields.DateTimeField', [], {}),
            'link_code': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['phone_auth.PhoneNumberLinkCode']"}),
            'message_template': ('django.db.models.fields.TextField', [], {}),
            'scheduled_delivery_time': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            'sms_sender_phone_override': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'time_delay_hours': ('django.db.models.fields.PositiveIntegerField', [], {})
        },
        u'invites_manager.smsinvitemessage': {
            'Meta': {'unique_together': "(('country_calling_code', 'time_delay_hours'),)", 'object_name': 'SMSInviteMessage'},
            'country_calling_code': ('django.db.models.fields.PositiveSmallIntegerField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message_template': ('django.db.models.fields.TextField', [], {}),
            'time_delay_hours': ('django.db.models.fields.PositiveIntegerField', [], {})
        },
        u'phone_auth.phonenumber': {
            'Meta': {'object_name': 'PhoneNumber'},
            'date_created': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'phone_number': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '32'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['phone_auth.User']"}),
            'verified': ('django.db.models.fields.BooleanField', [], {})
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
            'avatar_file': ('django.db.models.fields.CharField', [], {'default': "'s3:shotvibe-avatars-01:default-avatar-0054.jpg'", 'max_length': '128'}),
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
        }
    }

    complete_apps = ['invites_manager']
