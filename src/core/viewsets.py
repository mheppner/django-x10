"""Core viewsets."""
import logging

from django.core.cache import cache
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.decorators import detail_route, list_route
from rest_framework.exceptions import APIException, ParseError
from rest_framework.response import Response

from x10.interface import FirecrackerException
from x10.lock import CacheLockException
from .models import InvalidSignalError, RealPerson, Scene, Schedule, SolarSchedule, Unit
from .serializers import (CommandSerializer, SceneSerializer, ScheduleSerializer,
                          SolarScheduleSerializer, UnitSerializer)

logger = logging.getLogger(__name__)


class ServiceUnavailable(APIException):
    """Exception when the serial interface could not be used."""

    status_code = 503
    default_detail = 'Service temporarily unavailable, try again later.'


class UnitViewSet(viewsets.ModelViewSet):
    """Viewset for interacting with Unit models."""

    queryset = Unit.objects.all()
    serializer_class = UnitSerializer
    lookup_field = 'slug'
    filter_backends = [DjangoFilterBackend]
    filter_fields = ('dimmable', 'state')

    @detail_route(methods=['POST'])
    def signal(self, request, slug=None):
        """Child view to send a command to the unit."""
        serializer = CommandSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        unit = self.get_object()

        try:
            unit.send_signal(data['action'], data['multiplier'])
        except (CacheLockException, FirecrackerException):
            raise ServiceUnavailable
        except InvalidSignalError as e:
            raise ParseError(detail=str(e))

        return Response({'state': unit.state})


class SceneViewSet(viewsets.ModelViewSet):
    """Viewset for interacting with scenes."""

    queryset = Scene.objects.all()
    serializer_class = SceneSerializer
    lookup_field = 'slug'

    @detail_route(methods=['POST'])
    def signal(self, request, slug=None):
        """Child view to send a command to the scene."""
        serializer = CommandSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        scene = self.get_object()

        try:
            status = scene.send_signal(data['action'], data['multiplier'])
        except (CacheLockException, FirecrackerException):
            raise ServiceUnavailable
        except InvalidSignalError as e:
            raise ParseError(detail=str(e))

        return Response({'status': status})


class ScheduleViewSet(viewsets.ModelViewSet):
    """Viewset for interacting with Schedule models."""

    queryset = Schedule.objects.all()
    serializer_class = ScheduleSerializer


class SolarScheduleViewSet(viewsets.ModelViewSet):
    """Viewset for interacting with SolarSchedule models."""

    queryset = SolarSchedule.objects.all()
    serializer_class = SolarScheduleSerializer


class PersonViewSet(viewsets.ViewSet):
    """Viewset for controlling leave/arrive events for real people."""

    KEY = 'sticky_lights'

    def list(self, request):
        """Override list method to show the is_home state."""
        return Response({'is_home': RealPerson.is_home()})

    @list_route(methods=['POST'])
    def leave(self, request):
        """Child view when leaving to turn off all lights."""
        if not RealPerson.is_home():
            return Response({
                'message': 'Everyone has already left the house'
            })

        log = []

        # save the state that someone is home
        RealPerson.leave()
        logger.debug(f'real person has left')

        # save lights currently turned on
        on_units = Unit.objects.filter(state=True, auto_managed=True)
        on_units_slugs = [u.slug for u in on_units]
        cache.set(PersonViewSet.KEY, on_units_slugs, None)
        logger.debug(f'previously on units: {on_units_slugs}')

        # turn off all lights
        for unit in on_units:
            try:
                unit.send_signal(Unit.OFF_ACTION)
                log.append(f'Turned {unit} off')
                logger.info(f'turning {unit} off')
            except (CacheLockException, FirecrackerException):
                raise ServiceUnavailable

        return Response({
            'message': 'Have a nice day!',
            'log': log
        })

    @list_route(methods=['POST'])
    def arrive(self, request):
        """Child view when leaving to turn on lights that were previously on."""
        if RealPerson.is_home():
            return Response({
                'message': 'Another person has already entered the house'
            })

        log = []

        # save the state that someone is home
        RealPerson.arrive()

        # get the current time and any units that were on when someone left
        previously_on_units = cache.get(PersonViewSet.KEY, [])
        logger.debug(f'previously on units: {previously_on_units}')

        # turn on units that were on when last left
        for slug in previously_on_units:
            try:
                unit = Unit.objects.get(slug=slug)
            except Unit.DoesNotExist:
                logger.warn(f'{slug} does not exist, skipping')
            else:
                try:
                    unit.send_signal(Unit.ON_ACTION)
                    log.append(f'Turned {unit} back on')
                    logger.info(f'turning {unit} back on')
                except (CacheLockException, FirecrackerException):
                    raise ServiceUnavailable

        # turn on units that fall within their scheduled on times
        managed_units = Unit.objects.filter(state=False, auto_managed=True)
        for unit in managed_units.all():
            if unit.intended_state(only_if_home=True):
                try:
                    unit.send_signal(Unit.ON_ACTION)
                    log.append(f'Turned {unit} on due to a scheduled event')
                    logger.info('turned {unit} on due to an intended state')
                except (CacheLockException, FirecrackerException):
                    raise ServiceUnavailable

        return Response({
            'message': 'Welcome home!',
            'log': log
        })
