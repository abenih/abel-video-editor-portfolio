"""Turns the old fixed category codes into the words they used to display as.

``category`` used to be a choice field, so the page showed
``get_category_display()``. Now that it is free text the stored value *is* the
label, and every existing project has to be rewritten once or the site would
start showing "video" where it used to show "Video Editing".
"""
from django.db import migrations

# A copy of the retired CATEGORY_CHOICES, frozen here on purpose.
OLD_LABELS = {
    'video': 'Video Editing',
    'motion': 'Motion Graphics',
    'design': 'Graphic Design',
    'thumbnail': 'Thumbnail Design',
    'branding': 'Branding & Logo',
    'ai': 'Generative AI',
}
NEW_CODES = {label: code for code, label in OLD_LABELS.items()}


def forwards(apps, schema_editor):
    Project = apps.get_model('portfolio', 'Project')
    for code, label in OLD_LABELS.items():
        Project.objects.filter(category=code).update(category=label)


def backwards(apps, schema_editor):
    Project = apps.get_model('portfolio', 'Project')
    for label, code in NEW_CODES.items():
        Project.objects.filter(category=label).update(category=code)


class Migration(migrations.Migration):

    dependencies = [
        ('portfolio', '0010_alter_project_category'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
