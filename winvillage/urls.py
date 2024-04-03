"""
URL configuration for winvillage project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.apps import apps
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf.urls.static import static
from django.views.i18n import JavaScriptCatalog
from django.views.static import serve
from django.conf import settings
from django.conf.urls.i18n import i18n_patterns

urlpatterns = [
    path("__debug__/", include("debug_toolbar.urls")),
]
urlpatterns += i18n_patterns(
    path("__reload__/", include("django_browser_reload.urls")),
    path(settings.ADMIN_URL, admin.site.urls),
    path("", include("core.urls")),
    path("reservations/", include("reservations.urls")),
    path("winadmin/", include("winadmin.urls")),
    # path(
    #     "jsi18n/recurrence/",
    #     JavaScriptCatalog.as_view(packages=["recurrence"]),
    #     name="javascript-catalog",
    # ),
    prefix_default_language=False,
)

if apps.is_installed("rosetta"):
    urlpatterns += [path("rosetta/", include("rosetta.urls"))]

if settings.DEBUG:
    if apps.is_installed("pattern_library"):
        urlpatterns += [
            path(
                "pattern-library/",
                include("pattern_library.urls"),
                name="pattern-library",
            )
        ]
    # This will only work in development
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    urlpatterns += [
        re_path(r"^media/(?P<path>.*)", serve, {"document_root": settings.MEDIA_ROOT})
    ]
