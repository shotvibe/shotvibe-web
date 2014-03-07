from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.core.urlresolvers import reverse
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect, HttpResponse
from django.conf import settings
from functools import wraps

from affiliates.models import Organization, OrganizationUser, Event, EventLink
from affiliates.forms import EventForm, EventLinkForm, \
    EventInviteImportForm, EventInviteSendForm
from frontend.mobile_views import get_device

from photos.models import Album, Photo, PendingPhoto, AlbumMember
from photos import image_uploads
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
        return redirect('frontend.views.home')
    return wrapped_view


def organization_membership_required(view_f):
    @wraps(view_f)
    def wrapped_view(request, organization_code):
        try:
            organizationUser = request.user.organizationuser_set.get(
                organization__code=organization_code
            )
        except OrganizationUser.DoesNotExist:
            return HttpResponseRedirect(reverse('affiliates.views.index'))
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


@login_required
@event_mod_required
def event_invites(request, event):
    data = None
    err = None
    err_msg = None
    import_form = None
    invites_form = None
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
                data, err, err_msg = event.create_eventinvites(items)
                if not err:
                    import_form = EventInviteImportForm()
            else:
                err, err_msg = True, "Invalid Request"
    if not import_form:
        import_form = EventInviteImportForm()
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
def event_photos(request, event):
    album = event.album

    num_photos_added = 0
    num_photos_failed = 0

    if request.POST:
        if 'add_photos' in request.POST:
            pending_photos = []
            for f in request.FILES.getlist('photo_files'):

                pending_photo = PendingPhoto.objects.create(author=request.user)
                location, directory = pending_photo.bucket.split(':')
                if location != 'local':
                    raise ValueError('Unknown photo bucket location: ' + location)

                image_uploads.handle_file_upload(directory, pending_photo.photo_id, f.chunks())
                pending_photos.append(pending_photo)
                num_photos_added += 1

            # Upload pending photos
            now = timezone.now()
            photos = [pf.get_or_process_uploaded_image_and_create_photo(album, now) for pf in pending_photos]

            # TODO: If this function will be refactored to use Class Based Views
            # change sender from `request` to `self` (View instance)
            photos_added_to_album.send(sender=request,
                                       photos=photos,
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
    device = get_device(request.META.get('HTTP_USER_AGENT', '').lower())

    if device == 'android':
        app_url = settings.GOOGLE_PLAY_URL
    elif device == 'iphone':
        app_url = settings.APPLE_APP_STORE_URL
    else:
        app_url = None

    eventLink = get_object_or_404(EventLink, slug=slug)
    eventLink.incr_downloaded()

    res = HttpResponse(app_url, status=302)
    res['Location'] = app_url
    return res


def event_link(request, slug):
    device = get_device(request.META.get('HTTP_USER_AGENT', '').lower())

    if device == 'android':
        app_url = settings.GOOGLE_PLAY_URL
    elif device == 'iphone':
        app_url = settings.APPLE_APP_STORE_URL
    else:
        app_url = None

    eventLink = get_object_or_404(EventLink, slug=slug)
    eventLink.incr_visited()
    album = eventLink.event.album

    request.session['event'] = str(eventLink.event.pk)
    request.session['album'] = str(album.pk)

    return render(request, 'affiliates/event_link.html', {
        'eventLink': eventLink,
        'app_url': app_url,
        'device': device,
        'photos': album.get_invite_page_photos(),
    })
