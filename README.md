# Abel Shemeles (littlekingo) Portfolio Website

A dynamic portfolio and video editor showcase website built with Django 5.2.

- **Production Domain:** [littlekingo.duckdns.org](https://littlekingo.duckdns.org)
- **GitHub Repository:** [abenih/abel-video-editor-portfolio](https://github.com/abenih/abel-video-editor-portfolio)

---

## Features

- **Dynamic Showcase & Media Embeds (`ProjectVideo`):**
  - Supports YouTube, Vimeo, and direct MP4/video uploads.
  - Portrait (9:16 reels/TikTok) and Landscape (16:9) aspect ratios with auto-fit containers.
  - Video gallery with thumbnail fallback and lightbox detail view.
- **Click-to-Edit CMS (`portfolio.editing`):**
  - When logged in as owner (`abel`), an **"Edit this page"** bar allows direct on-page editing via modal panels without needing `/admin/`.
  - Edit bio, profile pictures, hero titles, stats, skills, categories, and project cards directly.
- **Theme & Branding Customization:**
  - Configurable palette (accent colors, background, typography) stored in `SiteProfile` and editable from the front end.
- **Reading Library App (`idea`):**
  - Auxiliary books and document viewer hosted under `/library/`.
- **Preconfigured Database & Uploads:**
  - Includes `db.sqlite3` with migrations 0001 through 0011 applied.
  - Seeded with Abel's profile, featured projects (weddings, concerts, game graphics, podcasts), skills, and media assets under `media/`.

---

## Quickstart (Local Development)

### 1. Activate Environment & Install Dependencies

```bash
cd littlekingo-portfolio
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Verify Migrations & Collect Static

```bash
python manage.py migrate
python manage.py collectstatic --noinput
```

### 3. Start Development Server

```bash
python manage.py runserver 127.0.0.1:8000
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser.

- Log in at `/login/` or `/admin/` to enable **"Edit this page"** mode.

---

## Deployment & Maintenance

Production scripts are located in `deploy/`:

- `deploy/update.sh`: Zero-downtime routine updates on the VPS (runs as user without sudo).
- `deploy/provision-vps.sh`: Full server setup script (systemd service, nginx vhost, certbot SSL).
- `deploy/backup.sh`: Automated backup script for `db.sqlite3` and `/var/www/kingo-portfolio/media`.
- `deploy/push.ps1`: Code deployment script.
- `DEPLOY_PYTHONANYWHERE.md`: Step-by-step guide for hosting on PythonAnywhere.

