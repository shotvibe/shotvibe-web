from django import forms
from django.contrib import admin

from affiliates.models import Organization, OrganizationUser, Event, EventLink


class OrganizationUserAdminInline(admin.TabularInline):
    model = OrganizationUser
    extra = 0


class OrganizationAdmin(admin.ModelAdmin):
    inlines = [OrganizationUserAdminInline]


class EventLinkAdminInline(admin.TabularInline):
    model = EventLink
    extra = 0


class EventAdmin(admin.ModelAdmin):
    inlines = [EventLinkAdminInline]


admin.site.register(Organization, OrganizationAdmin)
admin.site.register(Event, EventAdmin)
