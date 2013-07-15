# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'User'
        db.create_table(u'phone_auth_user', (
            ('password', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('last_login', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('is_superuser', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('id', self.gf('django.db.models.fields.IntegerField')(primary_key=True)),
            ('nickname', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('primary_email', self.gf('django.db.models.fields.related.ForeignKey')(related_name='+', on_delete=models.SET_NULL, to=orm['phone_auth.UserEmail'], blank=True, null=True, db_index=False)),
            ('date_joined', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('is_registered', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('is_staff', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('is_active', self.gf('django.db.models.fields.BooleanField')(default=True)),
        ))
        db.send_create_signal(u'phone_auth', ['User'])

        # Adding M2M table for field groups on 'User'
        m2m_table_name = db.shorten_name(u'phone_auth_user_groups')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('user', models.ForeignKey(orm[u'phone_auth.user'], null=False)),
            ('group', models.ForeignKey(orm[u'auth.group'], null=False))
        ))
        db.create_unique(m2m_table_name, ['user_id', 'group_id'])

        # Adding M2M table for field user_permissions on 'User'
        m2m_table_name = db.shorten_name(u'phone_auth_user_user_permissions')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('user', models.ForeignKey(orm[u'phone_auth.user'], null=False)),
            ('permission', models.ForeignKey(orm[u'auth.permission'], null=False))
        ))
        db.create_unique(m2m_table_name, ['user_id', 'permission_id'])

        # Adding model 'UserEmail'
        db.create_table(u'phone_auth_useremail', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['phone_auth.User'])),
            ('email', self.gf('django.db.models.fields.EmailField')(unique=True, max_length=75)),
        ))
        db.send_create_signal(u'phone_auth', ['UserEmail'])

        # Adding model 'AuthToken'
        db.create_table(u'phone_auth_authtoken', (
            ('key', self.gf('django.db.models.fields.CharField')(max_length=40, primary_key=True)),
            ('description', self.gf('django.db.models.fields.TextField')()),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['phone_auth.User'])),
            ('date_created', self.gf('django.db.models.fields.DateTimeField')()),
            ('last_access', self.gf('django.db.models.fields.DateTimeField')()),
            ('last_access_ip', self.gf('django.db.models.fields.GenericIPAddressField')(max_length=39, null=True, blank=True)),
        ))
        db.send_create_signal(u'phone_auth', ['AuthToken'])

        # Adding model 'PhoneNumber'
        db.create_table(u'phone_auth_phonenumber', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('phone_number', self.gf('django.db.models.fields.CharField')(unique=True, max_length=32)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['phone_auth.User'])),
            ('date_created', self.gf('django.db.models.fields.DateTimeField')(db_index=True)),
            ('verified', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal(u'phone_auth', ['PhoneNumber'])

        # Adding model 'PhoneNumberConfirmSMSCode'
        db.create_table(u'phone_auth_phonenumberconfirmsmscode', (
            ('confirmation_key', self.gf('django.db.models.fields.CharField')(max_length=40, primary_key=True)),
            ('confirmation_code', self.gf('django.db.models.fields.CharField')(max_length=6)),
            ('phone_number', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['phone_auth.PhoneNumber'])),
            ('date_created', self.gf('django.db.models.fields.DateTimeField')(db_index=True)),
        ))
        db.send_create_signal(u'phone_auth', ['PhoneNumberConfirmSMSCode'])

        # Adding model 'PhoneNumberLinkCode'
        db.create_table(u'phone_auth_phonenumberlinkcode', (
            ('invite_code', self.gf('django.db.models.fields.CharField')(max_length=32, primary_key=True)),
            ('phone_number', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['phone_auth.PhoneNumber'], unique=True)),
            ('inviting_user', self.gf('django.db.models.fields.related.ForeignKey')(related_name='+', to=orm['phone_auth.User'])),
            ('date_created', self.gf('django.db.models.fields.DateTimeField')(db_index=True)),
        ))
        db.send_create_signal(u'phone_auth', ['PhoneNumberLinkCode'])


    def backwards(self, orm):
        # Deleting model 'User'
        db.delete_table(u'phone_auth_user')

        # Removing M2M table for field groups on 'User'
        db.delete_table(db.shorten_name(u'phone_auth_user_groups'))

        # Removing M2M table for field user_permissions on 'User'
        db.delete_table(db.shorten_name(u'phone_auth_user_user_permissions'))

        # Deleting model 'UserEmail'
        db.delete_table(u'phone_auth_useremail')

        # Deleting model 'AuthToken'
        db.delete_table(u'phone_auth_authtoken')

        # Deleting model 'PhoneNumber'
        db.delete_table(u'phone_auth_phonenumber')

        # Deleting model 'PhoneNumberConfirmSMSCode'
        db.delete_table(u'phone_auth_phonenumberconfirmsmscode')

        # Deleting model 'PhoneNumberLinkCode'
        db.delete_table(u'phone_auth_phonenumberlinkcode')


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
        u'phone_auth.authtoken': {
            'Meta': {'object_name': 'AuthToken'},
            'date_created': ('django.db.models.fields.DateTimeField', [], {}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'key': ('django.db.models.fields.CharField', [], {'max_length': '40', 'primary_key': 'True'}),
            'last_access': ('django.db.models.fields.DateTimeField', [], {}),
            'last_access_ip': ('django.db.models.fields.GenericIPAddressField', [], {'max_length': '39', 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['phone_auth.User']"})
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
            'phone_number': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['phone_auth.PhoneNumber']", 'unique': 'True'})
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
        }
    }

    complete_apps = ['phone_auth']
