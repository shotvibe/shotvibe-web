from django.test import TestCase
from affiliates.models import Organization, OrganizationUser, Event, EventLink
from django.contrib import auth
from django.core.urlresolvers import reverse
from django.conf import settings
from django.db import IntegrityError, transaction
import django.utils.timezone

from affiliates.views import index, organization, create_event, event_edit, \
    event_links, event_invites, event_link, event_download_link


class ModelTests(TestCase):
    fixtures = ['tests/test_users']

    def test_organization_access(self):
        amanda = auth.get_user_model().objects.get(pk=2)
        barney = auth.get_user_model().objects.get(pk=3)
        chloe = auth.get_user_model().objects.get(pk=4)
        daniel = auth.get_user_model().objects.get(pk=5)
        org_a = Organization(code="a")
        org_a.save()
        org_b = Organization(code="b")
        org_b.save()
        org_ab = Organization(code="ab")
        org_ab.save()
        org_c = Organization(code="c")
        org_c.save()

        org_a.add_user(amanda)
        org_ab.add_user(amanda)
        org_b.add_user(barney)
        org_ab.add_user(barney)
        org_c.add_user(chloe)

        endpoint_items = [
            reverse(index),
            reverse(organization, args=(org_a,)),
            reverse(organization, args=(org_b,)),
            reverse(organization, args=(org_ab,)),
            reverse(organization, args=(org_c,)),
        ]
        access_matrix = {
            ('2', 'amanda'): [True, True, False, True, False],
            ('3', 'barney'): [True, False, True, True, False],
            ('4', 'chloe'): [False, False, False, False, True],
            ('5', 'daniel'): [False, False, False, False, False],
        }
        OKAY_RESPONSE = 200
        DENY_RESPONSE = 302

        for credentials, access_list in access_matrix.iteritems():
            self.client.login(username=credentials[0], password=credentials[1])
            for endpoint, access in zip(endpoint_items, access_list):
                r = self.client.get(endpoint)
                self.assertEqual(
                    r.status_code,
                    OKAY_RESPONSE if access else DENY_RESPONSE,
                )


class EventLinkTests(TestCase):
    fixtures = ['tests/test_users']

    def setUp(self):
        self.amanda = auth.get_user_model().objects.get(pk=2)
        self.org = Organization(code="a")
        self.org.save()
        self.org.add_user(self.amanda)
        now = django.utils.timezone.now()
        self.event = self.org.create_event(
            Event(name="event", time=now),
            self.amanda
        )

    def test_url_hashing(self):
        # check first 10.000 values
        n = 10000
        ids = range(n)
        seen_hashes = set()
        for i in ids:
            h = EventLink.encode_hash(i)
            r_i = EventLink.decode_hash(h)
            self.assertEqual(i, r_i)
            seen_hashes.add(h)
        # check for no collisions
        self.assertEqual(len(seen_hashes), n)

        # check some random custom url values
        vals = ['foobar', 'somecustomlink1']
        for val in vals:
            i = EventLink.decode_hash(val)
            r_h = EventLink.encode_hash(i)
            self.assertEqual(val, r_h)

        # check some random invalid url values
        vals = ['foo bar', 'somecustom/link']
        for val in vals:
            i = EventLink.decode_hash(val)
            self.assertEqual(i, None)

    def test_url_creation(self):
        n = 1000
        ids = range(n)
        for i in ids:
            eventLink = self.event.create_link()

        self.assertEqual(EventLink.objects.count(), n)

    def test_url_collision(self):
        n = 10
        ids = range(n)
        rev_slugs = []
        for i in ids:
            eventLink = self.event.create_link()
            rev_slugs.append(eventLink.slug)
        self.assertEqual(EventLink.objects.count(), n)
        for slug in rev_slugs:
            with self.assertRaises(IntegrityError):
                with transaction.atomic():
                    self.event.create_link(slug=slug)

    def test_url_collision_skip(self):
        vals = (5, 6, 4, 7, 8, 20)
        for i, val in enumerate(vals):
            slug = EventLink.encode_hash(val)
            eventLink = self.event.create_link(slug=slug)
            self.assertEquals(eventLink.pk, i+1)

        n = 10
        ids = range(n)
        for i in ids:
            eventLink = self.event.create_link()
        num_links = EventLink.objects.filter(event__isnull=False).count()
        self.assertEqual(num_links, n+len(vals))


class EventLinkVisitTests(TestCase):
    fixtures = ['tests/test_users']

    def setUp(self):
        self.amanda = auth.get_user_model().objects.get(pk=2)
        self.org = Organization(code="a")
        self.org.save()
        self.org.add_user(self.amanda)
        now = django.utils.timezone.now()
        self.event = self.org.create_event(
            Event(name="event", time=now),
            self.amanda,
        )

    def test_visited_count(self):
        eventLink = self.event.create_link()
        pk = eventLink.pk
        slug = eventLink.slug

        self.assertEqual(eventLink.visited_count, 0)

        for i in xrange(20):
            r = self.client.get(reverse(event_link, args=[slug]))
            #have to fetch link again
            eventLink = EventLink.objects.get(pk=pk)
            self.assertEqual(eventLink.visited_count, i + 1)

    def test_downloaded_count(self):
        eventLink = self.event.create_link()
        pk = eventLink.pk
        slug = eventLink.slug

        self.assertEqual(eventLink.visited_count, 0)

        for i in xrange(20):
            r = self.client.get(reverse(event_download_link, args=[slug]))
            self.assertEqual(r.status_code, 302)
            #have to fetch link again
            eventLink = EventLink.objects.get(pk=pk)
            self.assertEqual(eventLink.downloaded_count, i + 1)


class AffiliateCRUDTests(TestCase):
    fixtures = ['tests/test_users']

    def setUp(self):
        self.amanda = auth.get_user_model().objects.get(pk=2)
        self.org = Organization(code="a")
        self.org.save()
        self.org.add_user(self.amanda)
        self.client.login(username='2', password='amanda')

    def test_create_event(self):
        r = self.client.get(reverse(create_event, args=[self.org.code]))
        self.assertEqual(r.status_code, 200)
        data = {
            'name': 'Sample',
            'time_0': '18/02/2014 13:45',
            'sms_message': 'Test',
            'push_notification': 'Test',
            'location': 'Test',
            'html_content': """<ul>
    <li>Hey</li>
    <li>Hey</li>
</ul>""",
        }
        r = self.client.post(reverse(create_event, args=[self.org.code]), data)
        self.assertEqual(r.status_code, 302)

        #should redirect to new event
        event = self.org.event_set.all()[0]
        event_url = 'http://testserver' + \
            reverse(event_edit, args=[self.org.code, event.pk])
        self.assertEqual(r['Location'], event_url)

        #check fields were set correctly
        for field in ('name', 'sms_message', 'push_notification', 'location', 'html_content'):
            self.assertEqual(getattr(event, field), data.get(field))

    def test_edit_event(self):
        now = django.utils.timezone.now()
        event = self.org.create_event(
            Event(name="event", time=now),
            self.amanda
        )
        event_edit_url = reverse(event_edit, args=[self.org.code, event.pk])
        r = self.client.get(event_edit_url)
        self.assertEqual(r.status_code, 200)
        data = {
            'name': 'Sample',
            'time_0': '18/02/2014 13:45',
            'sms_message': 'Test',
            'push_notification': 'Test',
            'location': 'Test',
            'html_content': """<ul>
    <li>Hey</li>
    <li>Hey</li>
</ul>""",
        }
        r = self.client.post(event_edit_url, data)
        self.assertEqual(r.status_code, 200)

        event = Event.objects.get(pk=event.pk)
        #check fields were set correctly
        for field in ('name', 'sms_message', 'push_notification', 'location', 'html_content'):
            self.assertEqual(getattr(event, field), data.get(field))

    def test_create_new_link(self):
        now = django.utils.timezone.now()
        event = self.org.create_event(
            Event(name="event", time=now),
            self.amanda
        )
        event_links_url = reverse(event_links, args=[self.org.code, event.pk])
        r = self.client.get(event_links_url)
        self.assertEqual(r.status_code, 200)

        #test auto link creation
        data = {}

        for i in xrange(10):
            r = self.client.post(event_links_url, data)
            self.assertEqual(r.status_code, 200)
            self.assertEqual(event.links().count(), i+1)

    def test_import_numbers(self):
        now = django.utils.timezone.now()
        event = self.org.create_event(
            Event(name="event", time=now),
            self.amanda
        )
        invites_url = reverse(event_invites, args=[self.org.code, event.pk])
        r = self.client.get(invites_url)
        self.assertEqual(r.status_code, 200)

        #test auto link creation
        data = {
            'data': """somebody +18881231234
somebody else +18881234444""",
        }

        r = self.client.post(invites_url, data)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(event.eventinvites().count(), 2)

    def test_sms_send(self):
        from mock import patch
        now = django.utils.timezone.now()
        event = self.org.create_event(
            Event(name="event", time=now),
            self.amanda
        )
        event.create_eventinvites([
            ('test_user1', '+12127180000'),
            ('test_user2', '+12127180001'),
            ('test_user3', '+12127180002'),
        ])

        self.assertEqual(len(event.eventinvites()), 3)
        with patch("phone_auth.models.send_sms") as mock:
            event.send_invites(event.eventinvites())
            self.assertEqual(mock.call_count, 3)

    def test_multiple_sms_send(self):
        from mock import patch
        now = django.utils.timezone.now()
        event_a = self.org.create_event(
            Event(name="event_a", time=now),
            self.amanda
        )
        event_a.create_eventinvites([
            ('test_user1', '+12127180000'),
            ('test_user2', '+12127180001'),
        ])
        self.assertEqual(len(event_a.eventinvites()), 2)
        with patch("phone_auth.models.send_sms") as mock:
            event_a.send_invites(event_a.eventinvites())
            self.assertEqual(mock.call_count, 2)

        event_b = self.org.create_event(
            Event(name="event_b", time=now),
            self.amanda
        )
        event_b.create_eventinvites([
            ('test_user3', '+12127180000'),
            ('test_user4', '+12127180001'),
        ])

        self.assertEqual(len(event_b.eventinvites()), 2)
        with patch("phone_auth.models.send_sms") as mock:
            event_b.send_invites(event_b.eventinvites())
            self.assertEqual(mock.call_count, 2)
