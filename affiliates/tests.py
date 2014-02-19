from django.test import TestCase
from affiliates.models import Organization, OrganizationUser, Event, EventLink
from django.contrib import auth
from django.core.urlresolvers import reverse
from django.conf import settings
from django.db import IntegrityError, transaction
import django.utils.timezone

from affiliates.views import index, organization, create_event, event_edit, \
        event_link, event_download_link


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
            self.amanda
        )

    def test_visited_count(self):
        eventLink = self.event.create_link()
        pk = eventLink.pk
        slug = eventLink.slug

        self.assertEqual(eventLink.visited_count, 0)

        for i in xrange(20):
            r = self.client.get(reverse(event_link, args=[slug,]))
            #have to fetch link again
            eventLink = EventLink.objects.get(pk=pk)
            self.assertEqual(eventLink.visited_count, i + 1)

    def test_downloaded_count(self):
        eventLink = self.event.create_link()
        pk = eventLink.pk
        slug = eventLink.slug

        self.assertEqual(eventLink.visited_count, 0)

        for i in xrange(20):
            r = self.client.get(reverse(event_download_link, args=[slug,]))
            self.assertEqual(r.status_code, 302)
            #have to fetch link again
            eventLink = EventLink.objects.get(pk=pk)
            self.assertEqual(eventLink.downloaded_count, i + 1)
