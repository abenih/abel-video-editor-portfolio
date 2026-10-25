PythonAnywhere Free Deployment Guide

Repository
- https://github.com/abenih/abel-video-editor-portfolio

1. Create account and web app
- Sign in at https://www.pythonanywhere.com
- Go to Web tab
- Add a new web app
- Choose Manual configuration
- Choose Python 3.12

2. Open a Bash console and clone project
- cd ~
- git clone https://github.com/abenih/abel-video-editor-portfolio.git
- cd abel-video-editor-portfolio

3. Create virtual environment and install dependencies
- python3.12 -m venv venv
- source venv/bin/activate
- pip install --upgrade pip
- pip install -r requirements.txt

4. Initialize database and static files
- python manage.py migrate
- python manage.py collectstatic --noinput

5. Configure WSGI file
- Open: /var/www/<PA_USERNAME>_pythonanywhere_com_wsgi.py
- Replace or edit with:

import os
import sys

project_path = '/home/<PA_USERNAME>/abel-video-editor-portfolio'
if project_path not in sys.path:
    sys.path.insert(0, project_path)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sandbox.settings')
os.environ['DJANGO_SECRET_KEY'] = '<PUT_A_STRONG_SECRET_KEY>'
os.environ['DJANGO_DEBUG'] = 'False'
os.environ['DJANGO_ALLOWED_HOSTS'] = '<PA_USERNAME>.pythonanywhere.com'
os.environ['DJANGO_CSRF_TRUSTED_ORIGINS'] = 'https://<PA_USERNAME>.pythonanywhere.com'

from sandbox.wsgi import application

6. Configure static and media mappings in Web tab
- URL: /static/  Directory: /home/<PA_USERNAME>/abel-video-editor-portfolio/staticfiles
- URL: /media/   Directory: /home/<PA_USERNAME>/abel-video-editor-portfolio/media
- These mappings are served by PythonAnywhere itself, so requests for /media/ never reach the app. Leave DJANGO_WHITENOISE_AUTOREFRESH unset here.

7. Reload site
- Click Reload in Web tab

8. Open live URL
- https://<PA_USERNAME>.pythonanywhere.com

Notes
- Import `application` from `sandbox.wsgi` (not `get_wsgi_application()` directly) — that module wraps the app in WhiteNoise so uploaded media under /media/ is served even with DEBUG=False.
- This project stores uploaded media under the media folder, so the /media/ mapping must point there.
- `DJANGO_WHITENOISE_AUTOREFRESH` controls whether WhiteNoise re-checks the filesystem on every request. It defaults to on with `DJANGO_DEBUG=True` and off otherwise.
  - On PythonAnywhere, keep it off: the /media/ mapping above serves uploads directly, so new files appear immediately without it.
  - On a host with no platform-level /media/ mapping (WhiteNoise is doing the serving), set `os.environ['DJANGO_WHITENOISE_AUTOREFRESH'] = 'True'` alongside the other variables in the WSGI file, otherwise newly uploaded images 404 until the process is restarted.
  - The trade-off: WhiteNoise follows a directory symlink or junction inside the media folder out of that folder. With autorefresh off it only picks up links that already existed when the process started; with it on, links planted at any time are served. Only turn it on where nothing untrusted can write into that folder.
- If you edit content locally and want it online, commit and push changes, then pull on PythonAnywhere:
  - cd ~/abel-video-editor-portfolio
  - git pull
  - source venv/bin/activate
  - python manage.py migrate
  - python manage.py collectstatic --noinput
  - Reload web app in Web tab
