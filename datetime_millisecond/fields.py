import django.db.models.fields


class DateTimeMillisecondField(django.db.models.fields.DateTimeField):
    def db_type(self, connection):
        if connection.settings_dict['ENGINE'] == 'django.db.backends.postgresql_psycopg2':
            return 'timestamp (3) with time zone'
        else:
            return super(DateTimeMillisecondField, self).db_type(connection)

class TimeMillisecondField(django.db.models.fields.TimeField):
    def db_type(self, connection):
        if connection.settings_dict['ENGINE'] == 'django.db.backends.postgresql_psycopg2':
            return 'time (3)'
        else:
            return super(DateTimeMillisecondField, self).db_type(connection)
