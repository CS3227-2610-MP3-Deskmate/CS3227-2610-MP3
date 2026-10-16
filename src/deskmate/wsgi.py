"""WSGI entry point for the production Django runtime."""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "deskmate.settings")
application = get_wsgi_application()
