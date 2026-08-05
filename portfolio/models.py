import re

from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator, RegexValidator
from django.db import models
from django.urls import reverse

VIDEO_EXTENSIONS = ['mp4', 'mov', 'webm', 'm4v', 'avi']
IMAGE_EXTENSIONS = ['jpg', 'jpeg', 'png', 'webp', 'gif']

YOUTUBE_PATTERNS = [
    r'youtu\.be/([A-Za-z0-9_-]{6,})',
    r'youtube\.com/watch\?v=([A-Za-z0-9_-]{6,})',
    r'youtube\.com/embed/([A-Za-z0-9_-]{6,})',
    r'youtube\.com/shorts/([A-Za-z0-9_-]{6,})',
]
VIMEO_PATTERN = r'vimeo\.com/(?:video/)?(\d+)'
HEX_COLOR_PATTERN = r'^#(?:[0-9A-Fa-f]{3}|[0-9A-Fa-f]{6})$'


def extract_youtube_id(url):
    for pattern in YOUTUBE_PATTERNS:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def extract_vimeo_id(url):
    match = re.search(VIMEO_PATTERN, url)
    return match.group(1) if match else None


class Project(models.Model):
    CATEGORY_CHOICES = [
        ('video', 'Video Editing'),
        ('motion', 'Motion Graphics'),
        ('design', 'Graphic Design'),
        ('thumbnail', 'Thumbnail Design'),
        ('branding', 'Branding & Logo'),
        ('ai', 'Generative AI'),
    ]

    title = models.CharField(max_length=200)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='video')
    client = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)

    video_file = models.FileField(
        upload_to='projects/videos/',
        blank=True,
        null=True,
        validators=[FileExtensionValidator(VIDEO_EXTENSIONS)],
        help_text='Upload an MP4/MOV/WEBM file directly.',
    )
    video_url = models.URLField(
        blank=True,
        help_text='Paste a YouTube (unlisted works great) or Vimeo link instead of uploading a file.',
    )
    thumbnail = models.ImageField(
        upload_to='projects/thumbnails/',
        blank=True,
        null=True,
        validators=[FileExtensionValidator(IMAGE_EXTENSIONS)],
        help_text='Optional — a YouTube link will auto-generate one if left blank.',
    )

    is_featured = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0, help_text='Lower numbers appear first.')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_featured', 'order', '-created_at']

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('portfolio:project_detail', args=[self.pk])

    def clean(self):
        super().clean()
        if not self.video_file and not self.video_url:
            raise ValidationError('Add a video file or paste a video link (YouTube/Vimeo) first.')

    @property
    def youtube_id(self):
        return extract_youtube_id(self.video_url) if self.video_url else None

    @property
    def vimeo_id(self):
        return extract_vimeo_id(self.video_url) if self.video_url else None

    @property
    def embed_url(self):
        """A safe embeddable URL — only ever points at YouTube or Vimeo players."""
        if self.youtube_id:
            return f'https://www.youtube-nocookie.com/embed/{self.youtube_id}?rel=0'
        if self.vimeo_id:
            return f'https://player.vimeo.com/video/{self.vimeo_id}'
        return ''

    @property
    def display_thumbnail_url(self):
        if self.thumbnail:
            return self.thumbnail.url
        if self.youtube_id:
            return f'https://img.youtube.com/vi/{self.youtube_id}/hqdefault.jpg'
        return ''

    @property
    def has_playable_media(self):
        return bool(self.video_file or self.embed_url)


class ProjectImage(models.Model):
    """An extra gallery image for a project (e.g. additional design samples)."""

    project = models.ForeignKey(Project, related_name='gallery', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='projects/gallery/', validators=[FileExtensionValidator(IMAGE_EXTENSIONS)])
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return f'{self.project.title} — image {self.order + 1}'


# Icon names must match keys defined in portfolio/templatetags/portfolio_extras.py.
ICON_CHOICES = [
    ('video', 'Video camera'),
    ('motion', 'Film reel'),
    ('design', 'Overlapping circles'),
    ('thumbnail', 'Photo'),
    ('branding', 'Diamond'),
    ('ai', 'Sparkle'),
    ('clock', 'Clock'),
    ('check', 'Checkmark'),
    ('folder', 'Folder'),
    ('briefcase', 'Briefcase'),
    ('pin', 'Location pin'),
]


class SiteProfile(models.Model):
    """Singleton — the bio/contact info shown across the whole site. Edit via Admin."""

    name = models.CharField(max_length=200, default='Abel Shemeles')
    alias = models.CharField(max_length=100, blank=True, help_text='Short nickname shown in the nav bar.')
    title = models.CharField(max_length=200, help_text='Hero headline, e.g. "Video Editor & Visual Storyteller".')
    tagline = models.CharField(max_length=300, help_text='One-line summary shown under the headline and in the footer.')
    bio = models.TextField(blank=True, help_text='Full About Me paragraph.')
    highlight = models.CharField(max_length=300, blank=True, help_text='Short pull-quote shown under the bio.')
    since = models.CharField(max_length=10, blank=True, help_text='Year you started, e.g. 2021.')
    location = models.CharField(max_length=200, blank=True)
    phone = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    instagram = models.CharField(max_length=100, blank=True, help_text='Username only, without @.')
    facebook = models.CharField(max_length=100, blank=True, help_text='Username only.')
    telegram = models.CharField(max_length=100, blank=True, help_text='Username only.')
    show_experience_section = models.BooleanField(default=True, help_text='Show or hide the Experience section.')
    availability_text = models.CharField(max_length=120, default='Available for freelance work')
    hero_primary_cta_label = models.CharField(max_length=50, default='View My Work')
    hero_secondary_cta_label = models.CharField(max_length=50, default='Get In Touch')
    theme_bg = models.CharField(max_length=7, default='#08080c', validators=[RegexValidator(HEX_COLOR_PATTERN)])
    theme_bg_alt = models.CharField(max_length=7, default='#111117', validators=[RegexValidator(HEX_COLOR_PATTERN)])
    theme_text = models.CharField(max_length=7, default='#f3f3f7', validators=[RegexValidator(HEX_COLOR_PATTERN)])
    theme_text_muted = models.CharField(max_length=7, default='#9a9aac', validators=[RegexValidator(HEX_COLOR_PATTERN)])
    theme_accent = models.CharField(max_length=7, default='#7c5cff', validators=[RegexValidator(HEX_COLOR_PATTERN)])
    theme_accent_2 = models.CharField(max_length=7, default='#ff3d8f', validators=[RegexValidator(HEX_COLOR_PATTERN)])
    theme_accent_3 = models.CharField(max_length=7, default='#00e5c7', validators=[RegexValidator(HEX_COLOR_PATTERN)])
    hero_main_image = models.ImageField(
        upload_to='profile/', blank=True, null=True,
        validators=[FileExtensionValidator(IMAGE_EXTENSIONS)],
        help_text='Main portrait in the hero card.',
    )
    hero_badge_image = models.ImageField(
        upload_to='profile/', blank=True, null=True,
        validators=[FileExtensionValidator(IMAGE_EXTENSIONS)],
        help_text='Small floating hero image.',
    )
    hero_cutout_image = models.ImageField(
        upload_to='profile/', blank=True, null=True,
        validators=[FileExtensionValidator(IMAGE_EXTENSIONS)],
        help_text='Right-side hero cutout image.',
    )
    about_main_image = models.ImageField(
        upload_to='profile/', blank=True, null=True,
        validators=[FileExtensionValidator(IMAGE_EXTENSIONS)],
        help_text='First image in the about photo pair.',
    )
    about_side_image = models.ImageField(
        upload_to='profile/', blank=True, null=True,
        validators=[FileExtensionValidator(IMAGE_EXTENSIONS)],
        help_text='Second image in the about photo pair.',
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Site Profile'
        verbose_name_plural = 'Site Profile'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1, defaults={'title': 'Video Editor', 'tagline': ''})
        return obj


class Stat(models.Model):
    """A small headline stat shown in the hero, e.g. '3+ Years Editing'."""

    icon = models.CharField(max_length=20, choices=ICON_CHOICES, default='check')
    value = models.CharField(max_length=20, help_text='e.g. 3+, 20+, 100%')
    label = models.CharField(max_length=100)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return f'{self.value} {self.label}'


class Tool(models.Model):
    """A software/tool badge shown in the Tools & Skills section."""

    name = models.CharField(max_length=100)
    abbr = models.CharField(max_length=4, help_text='Short badge text, e.g. Pr, Ae, Ps.')
    bg = models.CharField(max_length=20, default='#1e1e2e', verbose_name='Badge background color')
    fg = models.CharField(max_length=20, default='#ffffff', verbose_name='Badge text color')
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return self.name


class SkillGroup(models.Model):
    """A category of skills, e.g. 'Video Editing', shown as its own card."""

    name = models.CharField(max_length=100)
    icon = models.CharField(max_length=20, choices=ICON_CHOICES, default='video')
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return self.name


class SkillItem(models.Model):
    group = models.ForeignKey(SkillGroup, related_name='items', on_delete=models.CASCADE)
    text = models.CharField(max_length=200)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return self.text


class ExperienceEntry(models.Model):
    """A row in the Experience timeline."""

    role = models.CharField(max_length=200)
    org = models.CharField(max_length=200, blank=True)
    period = models.CharField(max_length=100, help_text='e.g. 2022 — Present')
    description = models.TextField(blank=True)
    is_visible = models.BooleanField(default=True, help_text='Uncheck to hide this role from the public homepage.')
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']
        verbose_name_plural = 'Experience entries'

    def __str__(self):
        return self.role
