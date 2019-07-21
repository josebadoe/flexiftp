"""
WSGI config for ctusr project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/2.0/howto/deployment/wsgi/
"""

import os
import mod_wsgi

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ctusr.settings")
if mod_wsgi.process_group:
    os.environ['SITE_ROOT'] = "/%s" % mod_wsgi.process_group

application = get_wsgi_application()
