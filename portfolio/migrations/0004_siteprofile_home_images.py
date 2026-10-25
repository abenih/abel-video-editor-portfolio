from django.core.validators import FileExtensionValidator
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('portfolio', '0003_experienceentry_siteprofile_skillgroup_stat_tool_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='siteprofile',
            name='about_main_image',
            field=models.ImageField(
                blank=True,
                help_text='First image in the about photo pair.',
                null=True,
                upload_to='profile/',
                validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp', 'gif'])],
            ),
        ),
        migrations.AddField(
            model_name='siteprofile',
            name='about_side_image',
            field=models.ImageField(
                blank=True,
                help_text='Second image in the about photo pair.',
                null=True,
                upload_to='profile/',
                validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp', 'gif'])],
            ),
        ),
        migrations.AddField(
            model_name='siteprofile',
            name='hero_badge_image',
            field=models.ImageField(
                blank=True,
                help_text='Small floating hero image.',
                null=True,
                upload_to='profile/',
                validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp', 'gif'])],
            ),
        ),
        migrations.AddField(
            model_name='siteprofile',
            name='hero_cutout_image',
            field=models.ImageField(
                blank=True,
                help_text='Right-side hero cutout image.',
                null=True,
                upload_to='profile/',
                validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp', 'gif'])],
            ),
        ),
        migrations.AddField(
            model_name='siteprofile',
            name='hero_main_image',
            field=models.ImageField(
                blank=True,
                help_text='Main portrait in the hero card.',
                null=True,
                upload_to='profile/',
                validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp', 'gif'])],
            ),
        ),
    ]
