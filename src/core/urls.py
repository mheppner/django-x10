"""URLs for API and UI."""
from django.conf.urls import include, url
from rest_framework.authtoken.views import obtain_auth_token
from rest_framework.routers import DefaultRouter

from . import views


router = DefaultRouter()
router.register(r'person', views.PersonViewSet, base_name='person')
router.register(r'units', views.UnitViewSet)
router.register(r'scenes', views.SceneViewSet)


urlpatterns = [
    url(r'^token-auth/', obtain_auth_token),
    url(r'^auth/', include('rest_auth.urls')),
    url(r'^', include(router.urls, namespace='api')),
]
