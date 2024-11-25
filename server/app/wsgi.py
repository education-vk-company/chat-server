import os

from django.contrib import admin
from django.core.wsgi import get_wsgi_application
from django.urls import path

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.config.settings")

application = get_wsgi_application()

urlpatterns = [
    path("admin/", admin.site.urls),
]
