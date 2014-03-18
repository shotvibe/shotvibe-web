from datetimewidget.widgets import DateTimeWidget
from django.forms import Form, ModelForm
from django.forms import Textarea, CheckboxSelectMultiple
from django.forms import CharField, ModelMultipleChoiceField
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from affiliates.models import Event, EventLink, EventInvite, VALID_LINK_CHARS


class EventForm(ModelForm):
    class Meta:
        model = Event
        exclude = ['created_by', 'organization', 'album']
        widgets = {
            'time': DateTimeWidget()
        }


def validate_hash(h):
    invalids = set(c for c in h if c not in VALID_LINK_CHARS)
    if invalids:
        msgs = ["Invalid characters: "]
        msgs = msgs + list(invalids)
        raise ValidationError("".join(msgs))


class EventLinkForm(Form):
    slug = CharField(
        max_length=255,
        validators=[validate_hash],
        required=False
    )

    def create_link(self, event):
        try:
            eventLink = event.create_link(slug=self.cleaned_data['slug'])
        except IntegrityError:
            self._errors['slug'] = "Code already exists"
            return None
        else:
            return eventLink


class EventInviteImportForm(Form):
    default_country = CharField(required=False, min_length=2, max_length=2,
        label="2-Letter Country Code for phone numbers")
    data = CharField(required=True, widget=Textarea,
        label="Paste CSV")

    def clean_data(self):
        data = self.cleaned_data['data']
        items = EventInvite.import_data(data)
        self._items = items


class EventInviteSendForm(Form):
    invites = ModelMultipleChoiceField(
        queryset=EventInvite.objects.all(),
        widget=CheckboxSelectMultiple(),
    )

    def __init__(self, *args, **kwargs):
        try:
            queryset = kwargs.pop('queryset')
        except KeyError:
            queryset = None
        super(EventInviteSendForm, self).__init__(*args, **kwargs)
        if queryset is not None:
            self.fields['invites'].queryset = queryset
