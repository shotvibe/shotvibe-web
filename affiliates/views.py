import time

from django.contrib.auth.decorators import login_required
from django.contrib.gis.geoip import GeoIP, GeoIPException
from django.shortcuts import render, redirect, get_object_or_404
from django.core.urlresolvers import reverse
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import HttpResponseRedirect, HttpResponse, HttpResponseForbidden
from django.http import Http404
from django.conf import settings
from functools import wraps

import requests

from affiliates.models import Organization, OrganizationUser, Event, EventLink
from affiliates.forms import EventForm, EventLinkForm, \
    EventInviteImportForm, EventInviteSendForm
from frontend.user_device import get_device

from phone_auth.models import AuthToken
from photos.models import Album, Photo, PendingPhoto, AlbumMember
from photos import image_uploads
from photos import photo_operations
from photos_api.serializers import MemberIdentifier
from photos_api.signals import photos_added_to_album

from django.utils import timezone


def organization_required(view_f):
    @wraps(view_f)
    def wrapped_view(request):
        user = request.user
        orgs = [ou.organization for ou in user.organizationuser_set.all()]
        if orgs:
            return view_f(request, orgs)
        else:
            return HttpResponseForbidden("403 Forbidden.\nYou don't belong to any organizations. Try logging in as a different user.", content_type='text/plain')
    return wrapped_view


def organization_membership_required(view_f):
    @wraps(view_f)
    def wrapped_view(request, organization_code):
        try:
            organizationUser = request.user.organizationuser_set.get(
                organization__code=organization_code
            )
        except OrganizationUser.DoesNotExist:
            raise Http404
        else:
            return view_f(request, organizationUser.organization)
    return wrapped_view


def event_mod_required(view_f):
    @wraps(view_f)
    def wrapped_view(request, organization_code, event_id):
        try:
            event = Event.objects.get(
                id=event_id,
                organization__code=organization_code,
            )
            if not event.organization.is_member(request.user):
                raise PermissionDenied()
        except (Event.DoesNotExist, PermissionDenied) as e:
            return HttpResponseRedirect(reverse('affiliates.views.index'))
        else:
            return view_f(request, event)
    return wrapped_view


@login_required
@organization_required
def index(request, organizations):
    # if user only has one organization just send them there
    if len(organizations) == 1:
        return HttpResponseRedirect(reverse(
            'affiliates.views.organization',
            args=[organizations[0].code]
        ))

    return render(request, 'affiliates/index.html', {
        'organizations': organizations,
    })


@login_required
@organization_membership_required
def organization(request, organization):
    return render(request, 'affiliates/organization.html', {
        'organization': organization,
        'events': organization.event_set.all(),
    })


@login_required
@organization_membership_required
def create_event(request, organization):
    if request.method == 'POST':
        form = EventForm(request.POST)
        if form.is_valid():
            event = organization.create_event(
                form.save(commit=False),
                request.user,
            )
            return HttpResponseRedirect(reverse(
                'affiliates.views.event_edit',
                args=[organization.code, event.id]
            ))
    else:
        form = EventForm()
    return render(request, 'affiliates/create_event.html', {
        'organization': organization,
        'form': form,
    })


@login_required
@event_mod_required
def event_edit(request, event):
    if request.method == 'POST':
        form = EventForm(request.POST, instance=event)
        if form.is_valid():
            event = form.save()
    else:
        form = EventForm(instance=event)
    return render(request, 'affiliates/event/edit.html', {
        'organization': event.organization,
        'event': event,
        'form': form,
    })


@login_required
@event_mod_required
def event_links(request, event):
    if request.method == 'POST':
        form = EventLinkForm(request.POST)
        if form.is_valid():
            form.create_link(event)
    else:
        form = EventLinkForm()
    return render(request, 'affiliates/event/links.html', {
        'organization': event.organization,
        'event': event,
        'form': form,
    })


def get_request_country_code(request):
    try:
        g = GeoIP()
        country_code = g.country_code(request.META.get('REMOTE_ADDR'))
        del g
        return country_code
    except GeoIPException:
        return None


@login_required
@event_mod_required
def event_invites(request, event):
    country_code = get_request_country_code(request)
    data = None
    err = None
    err_msg = None
    import_form = None
    invites_form = None

    def new_blank_import_form():
        return EventInviteImportForm(initial={'default_country': country_code})

    if request.method == 'POST':
        action = request.POST.get("_action")
        if action == "invite":
            invites_form = EventInviteSendForm(
                request.POST,
                queryset=event.eventinvites(),
            )
            if invites_form.is_valid():
                event.send_invites(invites_form.cleaned_data['invites'])
        else:
            import_form = EventInviteImportForm(request.POST)
            if import_form.is_valid():
                items = import_form._items
                data, err, err_msg = event.create_eventinvites(items, import_form.cleaned_data['default_country'])
                if not err:
                    import_form = new_blank_import_form()
            else:
                err, err_msg = True, "Invalid Request"
    if not import_form:
        import_form = new_blank_import_form()
    if not invites_form:
        invites_form = EventInviteSendForm(queryset=event.eventinvites())
    return render(request, 'affiliates/event/invites.html', {
        'organization': event.organization,
        'event': event,
        'import_form': import_form,
        'data': data,
        'invites_form_fields': invites_form.fields['invites'],
        'err': err,
        'err_msg': err_msg,
    })


@login_required
@event_mod_required
def event_reports(request, event):
    return render(request, 'affiliates/event/reports.html', {
        'organization': event.organization,
        'event': event,
    })


@login_required
@event_mod_required
@transaction.non_atomic_requests
def event_photos(request, event):
    album = event.album

    num_photos_added = 0
    num_photos_failed = 0

    if request.POST:
        if 'add_photos' in request.POST:
            pending_photo_ids = []
            for f in request.FILES.getlist('photo_files'):

                pending_photo = Photo.objects.upload_request(author=request.user)

                if settings.USING_LOCAL_PHOTOS:
                    image_uploads.process_file_upload(pending_photo, f.chunks())
                else:
                    # Forward request to photo upload server
                    userAuthToken = AuthToken.objects.create_auth_token(request.user, 'Internal Photo Upload Auth Token', timezone.now())

                    r = requests.put(settings.PHOTO_UPLOAD_SERVER_URL + '/photos/upload/' + pending_photo.photo_id + '/original/',
                            headers = { 'Authorization': 'Token ' + userAuthToken.key },
                            data = f.chunks())
                    r.raise_for_status()

                pending_photo_ids.append(pending_photo.photo_id)

                num_photos_added += 1

            # Upload pending photos
            done = False
            total_retry_time = 0
            while not done:
                now = timezone.now()
                try:
                    photo_operations.add_pending_photos_to_album(pending_photo_ids, album.id, now)
                    done = True
                except RuntimeError:
                    # TODO This is a really bad workaround to deal with the
                    # situation where the photos aren't "done" yet (in which
                    # case "add_pending_photos_to_album" currently raises a
                    # "RuntimeError")
                    RETRY_TIME = 5
                    MAX_RETRY_TIME = 600 # 10 minutes

                    if total_retry_time >= MAX_RETRY_TIME:
                        raise

                    time.sleep(RETRY_TIME)
                    total_retry_time += RETRY_TIME

            # TODO: If this function will be refactored to use Class Based Views
            # change sender from `request` to `self` (View instance)
            photos_added_to_album.send(sender=request,
                                       photos=pending_photo_ids,
                                       by_user=request.user,
                                       to_album=album)

    data = {
            'event': event,
            'organization': event.organization,
            'album': album,
            'photos': album.get_photos(),
            'members': album.get_member_users(),
            'num_photos_added': num_photos_added,
            'num_photos_failed': num_photos_failed
            }
    return render(request, 'affiliates/event/photos.html', data)


def event_download_link(request, slug):
    device = get_device(request.META.get('HTTP_USER_AGENT', ''))

    if device.os == 'Android':
        app_url = settings.GOOGLE_PLAY_URL
    elif device.os == 'iOS':
        app_url = settings.APPLE_APP_STORE_URL
    else:
        app_url = None

    eventLink = get_object_or_404(EventLink, slug=slug)
    eventLink.incr_downloaded()

    res = HttpResponse(app_url, status=302)
    res['Location'] = app_url
    return res


def event_link(request, slug):
    device = get_device(request.META.get('HTTP_USER_AGENT', ''))

    if device.os == 'Android':
        app_url = settings.GOOGLE_PLAY_URL
    elif device.os == 'iOS':
        app_url = settings.APPLE_APP_STORE_URL
    else:
        app_url = None

    eventLink = get_object_or_404(EventLink, slug=slug)
    eventLink.incr_visited()
    album = eventLink.event.album

    request.session['custom_payload'] = "event:{0}".format(eventLink.event.pk)

    return render(request, 'frontend/mobile/invite_page.html', {
        'event': eventLink.event,
        'album': album,
        'app_url': app_url,
        'device': device,
        'app_button_text': eventLink.event.app_button_custom_text
    })
