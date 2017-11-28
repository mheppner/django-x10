"""URLs for API and UI."""
from django.conf.urls import include, url
from rest_framework.authtoken.views import obtain_auth_token
from rest_framework.routers import DefaultRouter

from . import viewsets


router = DefaultRouter()
router.register(r'person', viewsets.PersonViewSet, base_name='person')
router.register(r'units', viewsets.UnitViewSet)
router.register(r'scenes', viewsets.SceneViewSet)
router.register(r'schedules', viewsets.ScheduleViewSet)
router.register(r'solar-schedules', viewsets.SolarScheduleViewSet)


urlpatterns = [
    url(r'^token-auth/', obtain_auth_token),
    url(r'^auth/', include('rest_auth.urls')),
    url(r'^', include(router.urls, namespace='api')),
]
