"""Copies each project's single video onto a ProjectVideo row.

This runs against live data, so it is deliberately narrow: it only ever *reads*
``Project.video_file`` / ``Project.video_url``, it copies the stored file *name*
rather than the file, and it skips any project that already has video rows — so
re-running it is a no-op instead of a duplicate.
"""
from django.db import migrations

# A copy, not an import: a historical migration must not follow future model code.
VERTICAL_HINTS = ('youtube.com/shorts/', 'tiktok.com')


def _looks_vertical(url):
    lowered = (url or '').lower()
    return any(hint in lowered for hint in VERTICAL_HINTS)


def forwards(apps, schema_editor):
    Project = apps.get_model('portfolio', 'Project')
    ProjectVideo = apps.get_model('portfolio', 'ProjectVideo')
    for project in Project.objects.all().iterator():
        if not (project.video_file or project.video_url):
            continue
        if ProjectVideo.objects.filter(project=project).exists():
            continue
        ProjectVideo.objects.create(
            project=project,
            # .name is the MEDIA_ROOT-relative string, so no file is opened, moved or copied.
            video_file=project.video_file.name if project.video_file else '',
            video_url=project.video_url or '',
            orientation='portrait' if _looks_vertical(project.video_url) else 'landscape',
            is_cover=True,
            order=0,
        )


def backwards(apps, schema_editor):
    """Intentionally empty — the source columns were never modified, so there is
    nothing to restore. Deleting the copies would throw away rows the owner may
    have edited since."""


class Migration(migrations.Migration):

    dependencies = [
        ('portfolio', '0008_projectvideo_tool_icon_siteprofile_about_video'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
