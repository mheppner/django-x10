"""Admin panel options for core app."""
from adminsortable2.admin import SortableAdminMixin
from django.contrib import admin, messages
from guardian.admin import GuardedModelAdmin

from x10.interface import FirecrackerException
from x10.lock import CacheLockException
from . models import Scene, Schedule, SolarSchedule, Unit


@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    """Model options for Schedule models."""

    fieldsets = (
        (None, {
            'fields': ('crontab',)
        }),
    )
    list_display = ('crontab',)
    search_fields = ('crontab',)


@admin.register(SolarSchedule)
class SolarScheduleAdmin(admin.ModelAdmin):
    """Model options for SolarSchedule models."""

    fieldsets = (
        (None, {
            'fields': ('event',)
        }),
    )
    list_display = ('event',)
    search_fields = ('event',)


@admin.register(Unit)
class UnitAdmin(SortableAdminMixin, GuardedModelAdmin):
    """Model options for Unit models."""

    def _action(self, request, queryset, action):
        """Run an admin action on a set of units."""
        success = []
        fail = []
        for unit in queryset.all():
            try:
                unit.send_signal(action)
            except (CacheLockException, FirecrackerException):
                fail.append(str(unit.slug))
            else:
                success.append(str(unit.slug))
        if len(success):
            success = ', '.join(success)
            self.message_user(request, f'Sent task to turn {action} units: {success}')
        if len(fail):
            fail = ', '.join(fail)
            self.message_user(request,
                              f'Could not send task to turn {action} units: {fail}',
                              level=messages.ERROR)

    def turn_on(self, request, queryset):
        """Admin action to turn on units."""
        self._action(request, queryset, Unit.ON_ACTION)
    turn_on.short_description = 'Turn on'

    def turn_off(self, request, queryset):
        """Admin action to turn off units."""
        self._action(request, queryset, Unit.OFF_ACTION)
    turn_off.short_description = 'Turn off'

    fieldsets = (
        (None, {
            'fields': (('name', 'slug', 'state',),
                       ('house', 'number',),
                       ('dimmable', 'auto_managed'))
        }),
        ('Schedule', {
            'fields': ('on_schedules', 'off_schedules',
                       'on_solar_schedules', 'off_solar_schedules')
        })
    )
    list_display = ('slug', 'name', 'state', 'house', 'number', 'dimmable', 'auto_managed')
    list_editable = ('name', 'house', 'number', 'dimmable', 'auto_managed')
    list_filter = ('house', 'dimmable',)
    search_fields = ('name', 'slug', 'house', 'number',)
    readonly_fields = ('state',)
    prepopulated_fields = {'slug': ('name',)}
    actions = ['turn_on', 'turn_off']


@admin.register(Scene)
class SceneAdmin(admin.ModelAdmin):
    """Model options for Scene models."""

    fieldsets = (
        (None, {
            'fields': (('name', 'slug'), 'units')
        }),
    )
    filter_horizontal = ('units',)
    list_display = ('slug', 'name')
    list_filter = ()
    search_fields = ('units__name', 'units__slug', 'units__house', 'units__number', 'name',
                     'slug')
    prepopulated_fields = {'slug': ('name',)}
