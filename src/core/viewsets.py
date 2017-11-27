"""Core viewsets."""
from django.core.cache import cache
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.decorators import detail_route, list_route
from rest_framework.exceptions import APIException, ParseError
from rest_framework.response import Response

from x10.interface import FirecrackerException
from x10.lock import CacheLockException
from .models import InvalidSignalError, RealPerson, Scene, Unit
from .serializers import CommandSerializer, SceneSerializer, UnitSerializer


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


class PersonViewSet(viewsets.ViewSet):
    """Viewset for controlling leave/arrive events for real people."""

    KEY = 'sticky_lights'

    def list(self, request):
        """Override list method to show the is_home state."""
        return Response({'is_home': RealPerson.is_home()})

    @list_route(methods=['POST'])
    def leave(self, request):
        """Child view when leaving to turn off all lights."""
        log = []

        # save the state that someone is home
        RealPerson.leave()

        # save lights currently turned on
        on_units = Unit.objects.filter(state=True, auto_managed=True)
        cache.set(PersonViewSet.KEY, [u.slug for u in on_units], None)

        # turn off all lights
        for unit in on_units:
            try:
                unit.send_signal(Unit.OFF_ACTION)
                log.append(f'Turned {unit} off')
            except (CacheLockException, FirecrackerException):
                raise ServiceUnavailable

        return Response({
            'message': 'Have a nice day!',
            'log': log
        })

    @list_route(methods=['POST'])
    def arrive(self, request):
        """Child view when leaving to turn on lights that were previously on."""
        log = []

        # save the state that someone is home
        RealPerson.arrive()

        # get the current time and any units that were on when someone left
        previously_on_units = cache.get(PersonViewSet.KEY, [])

        # turn on units that were on when last left
        for slug in previously_on_units:
            try:
                unit = Unit.objects.get(slug=slug)
            except Unit.DoesNotExist:
                pass
            else:
                try:
                    unit.send_signal(Unit.ON_ACTION)
                    log.append(f'Turned {unit} back on')
                except (CacheLockException, FirecrackerException):
                    raise ServiceUnavailable

        # turn on units that fall within their scheduled on times
        managed_units = Unit.objects.filter(state=False, auto_managed=True)
        for unit in managed_units.all():
            if unit.intended_state():
                try:
                    unit.send_signal(Unit.ON_ACTION)
                    log.append(f'Turned {unit} on due to a scheduled event')
                except (CacheLockException, FirecrackerException):
                    raise ServiceUnavailable

        return Response({
            'message': 'Welcome home!',
            'log': log
        })
