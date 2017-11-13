"""Celery tasks for the core app."""
from __future__ import absolute_import

from celery import chain

from x10.celery import app
from . models import RealPerson, Unit
from . serializers import CommandSerializer


@app.task
def run_action(unit: str, action: str, multiplier: int=1, only_if_home: bool=False):
    """Run the given action for the unit.

    :param unit: the slug of the Unit model
    :param action: the action to send (on, off, brt, dim)
    :param multiplier: the number of times to send the signal
    :param only_if_home: only send the signal if a real person is home
    :raises: Unit.DoesNotExist, CacheLockException, ValidationError
    """
    print(f'run_action ({unit} - {action}): starting')

    if only_if_home and not RealPerson.is_home():
        print(f'run_action ({unit} - {action}): only if home flag was set and a person is not '
              'home, exiting')
        return

    # get the unit and let validate the input
    unit = Unit.objects.get(slug=unit)
    serializer = CommandSerializer(data={
        'action': action,
        'multiplier': multiplier,
    })
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    if data['action'] in ('on', 'off'):
        unit.state = data['action'] == 'on'
        unit.save()
    else:
        # either a brt or dim command
        unit.send_signal(data['action'], data['multiplier'])


@app.task
def run_group(slugs: list, action: str, multiplier: int=1, only_if_home: bool=False):
    """Send the same commands to multiple units."""
    print(f'run_group ({slugs}): starting')

    tasks = []
    for slug in slugs:
        tasks.append(
            run_action.s(slug, action, multiplier, only_if_home))

    chain(tasks).apply_async()
