"""Admin panel options for core app."""
from adminsortable2.admin import SortableAdminMixin
from django.contrib import admin
from guardian.admin import GuardedModelAdmin

from . models import Scene, Unit
from . tasks import run_group


@admin.register(Unit)
class UnitAdmin(SortableAdminMixin, GuardedModelAdmin):
    """Model options for Unit models."""

    def _action(self, request, queryset, action):
        """Run an admin action on a set of units."""
        units = list(queryset.values_list('slug', flat=True))
        units_str = ', '.join(units)
        run_group.delay(units, action)
        self.message_user(request, f'Sent task to turn {action} units: {units_str}')

    def turn_on(self, request, queryset):
        """Admin action to turn on units."""
        self._action(request, queryset, 'on')
    turn_on.short_description = 'Turn on'

    def turn_off(self, request, queryset):
        """Admin action to turn off units."""
        self._action(request, queryset, 'off')
    turn_off.short_description = 'Turn off'

    fieldsets = (
        (None, {
            'fields': (('name', 'slug', 'state',),
                       ('house', 'number',),
                       ('dimmable', 'auto_managed'))
        }),
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
