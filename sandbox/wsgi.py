"""
WSGI config for sandbox project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sandbox.settings')

application = get_wsgi_application()

# Uploaded media has to be served by the app itself so it keeps working with DEBUG=False
# on any host.
from django.conf import settings  # noqa: E402  (import must follow get_wsgi_application)
from whitenoise import WhiteNoise  # noqa: E402

# SecurityMiddleware runs inside this wrapper, so it never sees media responses and these
# headers have to be attached here. PDFs stay inline because the library reader iframes them.
_INLINE_TYPES = ('image/', 'video/', 'audio/', 'application/pdf')


def _media_headers(headers, path, url):
    headers['X-Content-Type-Options'] = 'nosniff'
    if not headers.get('Content-Type', '').startswith(_INLINE_TYPES):
        headers['Content-Disposition'] = 'attachment'


# autorefresh is opt-in (see WHITENOISE_AUTOREFRESH in settings): it makes fresh uploads
# visible without a restart, at the cost of also serving junctions/symlinks planted in
# MEDIA_ROOT after start-up. WhiteNoise resolves paths lexically, so links are followed out
# of MEDIA_ROOT; with autorefresh off only ones present at start-up are picked up.
application = WhiteNoise(
    application,
    autorefresh=settings.WHITENOISE_AUTOREFRESH,
    add_headers_function=_media_headers,
)
application.add_files(settings.MEDIA_ROOT, prefix=settings.MEDIA_URL)
