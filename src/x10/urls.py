"""Main project URL config."""
from django.conf import settings
from django.conf.urls import include, url
from django.contrib import admin

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^health/', include('health_check.urls')),
    url(r'^', include('core.urls', namespace='core')),
]


if settings.DEBUG:
    from django.conf.urls.static import static

    urlpatterns += static(settings.STATIC_URL,
                          document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL,
                          document_root=settings.MEDIA_ROOT)

    try:
        import debug_toolbar
    except ImportError:
        pass
    else:
        urlpatterns += [url(r'^__debug__/', include(debug_toolbar.urls)), ]
