from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('portfolio', '0009_move_project_videos'),
    ]

    operations = [
        migrations.AlterField(
            model_name='project',
            name='category',
            field=models.CharField(default='Video Editing', help_text='The small label under the title, e.g. "Video Editing" or "Podcast video".', max_length=60),
        ),
    ]
