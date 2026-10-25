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
TIKTOK_PATTERNS = [
    r'tiktok\.com/@[\w.\-]{1,30}/(?:video|photo)/(\d{6,25})',
    r'tiktok\.com/(?:v|embed)/(\d{6,25})',
    r'tiktok\.com/player/v1/(\d{6,25})',
]
HEX_COLOR_PATTERN = r'^#(?:[0-9A-Fa-f]{3}|[0-9A-Fa-f]{6})$'

ORIENTATION_CHOICES = [
    ('landscape', 'Wide — 16:9'),
    ('portrait', 'Tall — 9:16 (TikTok, Reels, Shorts)'),
    ('square', 'Square — 1:1'),
]

_ASPECT_CLASSES = {
    'landscape': 'is-landscape',
    'portrait': 'is-portrait',
    'square': 'is-square',
}

# The only origins an embed iframe may ever point at. Mirrored in main.js.
PROVIDER_ORIGINS = {
    'youtube': 'https://www.youtube-nocookie.com',
    'vimeo': 'https://player.vimeo.com',
    'tiktok': 'https://www.tiktok.com',
}

# TikTok is missing on purpose. Its player/v1 embed reached "playing" in only 3 of 10
# cold loads during the provider spike; the rest stalled in `buffering` and painted a
# black rectangle. It gets a poster and a play badge instead of a hover preview.
HOVER_PREVIEW_PROVIDERS = ('file', 'youtube', 'vimeo')

# Category is free text, so the little icon beside it is matched on wording.
# Anything unrecognised simply renders without an icon.
CATEGORY_ICONS = {
    'video editing': 'video',
    'video': 'video',
    'motion graphics': 'motion',
    'motion': 'motion',
    'graphic design': 'design',
    'design': 'design',
    'thumbnail design': 'thumbnail',
    'thumbnail': 'thumbnail',
    'branding & logo': 'branding',
    'branding': 'branding',
    'generative ai': 'ai',
    'ai': 'ai',
}

# Handles are pasted straight into https://instagram.com/<handle> etc. in the footer,
# so anything outside a plain username could point the link somewhere else entirely.
SOCIAL_HANDLE_VALIDATOR = RegexValidator(
    r'^[A-Za-z0-9._]{1,30}$',
    'Enter just the username — up to 30 letters, numbers, dots or underscores, with no @, spaces or slashes.',
)


def extract_youtube_id(url):
    for pattern in YOUTUBE_PATTERNS:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def extract_vimeo_id(url):
    match = re.search(VIMEO_PATTERN, url)
    return match.group(1) if match else None


def extract_tiktok_id(url):
    for pattern in TIKTOK_PATTERNS:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def category_icon_for(label):
    return CATEGORY_ICONS.get((label or '').strip().lower(), '')


class Project(models.Model):
    title = models.CharField(max_length=200)
    category = models.CharField(
        max_length=60,
        default='Video Editing',
        help_text='The small label under the title, e.g. "Video Editing" or "Podcast video".',
    )
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
        # The last condition only applies to a saved row — an unsaved one has no children yet.
        if not (self.video_file or self.video_url or self.thumbnail or (self.pk and self.videos.exists())):
            raise ValidationError(
                'Add a video, paste a video link (YouTube/Vimeo), or upload a cover picture — '
                'a piece needs at least one of these to show up on your site.'
            )

    @property
    def display_category(self):
        return self.category

    @property
    def category_icon(self):
        return category_icon_for(self.category)

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
    def cover_video(self):
        """Meta.ordering already puts the chosen cover first."""
        return self.videos.first()

    @property
    def video_count(self):
        return self.videos.count()

    @property
    def display_thumbnail_url(self):
        if self.thumbnail:
            return self.thumbnail.url
        cover = self.cover_video
        if cover and cover.poster_url:
            return cover.poster_url
        if self.youtube_id:
            return f'https://img.youtube.com/vi/{self.youtube_id}/hqdefault.jpg'
        return ''

    @property
    def has_playable_media(self):
        return bool(self.video_file or self.embed_url or self.videos.all())


class ProjectImage(models.Model):
    """An extra gallery image for a project (e.g. additional design samples)."""

    project = models.ForeignKey(Project, related_name='gallery', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='projects/gallery/', validators=[FileExtensionValidator(IMAGE_EXTENSIONS)])
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return f'{self.project.title} — image {self.order + 1}'


class ProjectVideo(models.Model):
    """One video inside a project's collection — either an upload or a link."""

    project = models.ForeignKey(Project, related_name='videos', on_delete=models.CASCADE)
    title = models.CharField(max_length=200, blank=True)
    video_file = models.FileField(
        upload_to='projects/videos/',
        blank=True,
        null=True,
        validators=[FileExtensionValidator(VIDEO_EXTENSIONS)],
    )
    video_url = models.URLField(blank=True)
    poster = models.ImageField(
        upload_to='projects/posters/',
        blank=True,
        null=True,
        validators=[FileExtensionValidator(IMAGE_EXTENSIONS)],
    )
    orientation = models.CharField(max_length=12, choices=ORIENTATION_CHOICES, default='landscape')
    is_cover = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-is_cover', 'order', 'id']

    def __str__(self):
        return self.title or f'{self.project.title} — video {self.order + 1}'

    @property
    def youtube_id(self):
        return extract_youtube_id(self.video_url) if self.video_url else None

    @property
    def vimeo_id(self):
        return extract_vimeo_id(self.video_url) if self.video_url else None

    @property
    def tiktok_id(self):
        return extract_tiktok_id(self.video_url) if self.video_url else None

    @property
    def provider(self):
        if self.video_file:
            return 'file'
        if self.youtube_id:
            return 'youtube'
        if self.vimeo_id:
            return 'vimeo'
        if self.tiktok_id:
            return 'tiktok'
        return ''

    @property
    def embed_url(self):
        """Click-to-play URL, rebuilt from an extracted id — never the pasted link."""
        if self.youtube_id:
            return f'https://www.youtube-nocookie.com/embed/{self.youtube_id}?rel=0'
        if self.vimeo_id:
            return f'https://player.vimeo.com/video/{self.vimeo_id}?dnt=1'
        if self.tiktok_id:
            return f'https://www.tiktok.com/player/v1/{self.tiktok_id}?rel=0&description=0&music_info=0'
        return ''

    @property
    def preview_embed_url(self):
        """Muted, looping autoplay URL used for hover previews. Same id-only rule."""
        if self.youtube_id:
            return (
                f'https://www.youtube-nocookie.com/embed/{self.youtube_id}'
                '?autoplay=1&mute=1&playsinline=1&controls=0&rel=0&modestbranding=1'
                f'&loop=1&playlist={self.youtube_id}'
            )
        if self.vimeo_id:
            return f'https://player.vimeo.com/video/{self.vimeo_id}?background=1&autoplay=1&muted=1&loop=1&dnt=1'
        if self.tiktok_id:
            return (
                f'https://www.tiktok.com/player/v1/{self.tiktok_id}'
                '?autoplay=1&muted=1&loop=1&controls=0&progress_bar=0&play_button=0'
                '&volume_control=0&fullscreen_button=0&timestamp=0'
                '&description=0&music_info=0&closed_caption=0&rel=0'
            )
        return ''

    @property
    def poster_url(self):
        if self.poster:
            return self.poster.url
        if self.youtube_id:
            return f'https://img.youtube.com/vi/{self.youtube_id}/hqdefault.jpg'
        return ''

    @property
    def aspect_class(self):
        return _ASPECT_CLASSES.get(self.orientation, 'is-landscape')

    @property
    def preview_kind(self):
        """What a *hover* should mount: 'file' | 'iframe' | '' (no hover preview)."""
        provider = self.provider
        if provider not in HOVER_PREVIEW_PROVIDERS:
            return ''
        return 'file' if provider == 'file' else 'iframe'

    @property
    def play_kind(self):
        """What a *click* should mount. Every provider is playable on demand."""
        if self.provider == 'file':
            return 'file'
        return 'iframe' if self.embed_url else ''

    @property
    def preview_origin(self):
        return PROVIDER_ORIGINS.get(self.provider, '')


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
    instagram = models.CharField(
        max_length=100, blank=True, help_text='Username only, without @.',
        validators=[SOCIAL_HANDLE_VALIDATOR],
    )
    facebook = models.CharField(
        max_length=100, blank=True, help_text='Username only.',
        validators=[SOCIAL_HANDLE_VALIDATOR],
    )
    telegram = models.CharField(
        max_length=100, blank=True, help_text='Username only.',
        validators=[SOCIAL_HANDLE_VALIDATOR],
    )
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
    about_video_file = models.FileField(
        upload_to='profile/videos/', blank=True, null=True,
        validators=[FileExtensionValidator(VIDEO_EXTENSIONS)],
        help_text='Video shown in the panel beside the About Me text.',
    )
    about_video_url = models.URLField(
        blank=True,
        help_text='YouTube, Vimeo or TikTok link used instead of an upload.',
    )
    about_video_poster = models.ImageField(
        upload_to='profile/', blank=True, null=True,
        validators=[FileExtensionValidator(IMAGE_EXTENSIONS)],
        help_text='Still image shown before the about video plays.',
    )
    about_video_orientation = models.CharField(
        max_length=12, choices=ORIENTATION_CHOICES, default='landscape',
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

    @property
    def about_video(self):
        """The About panel's video as an unsaved ProjectVideo, or None.

        Borrowing the child model means the provider, embed and orientation rules
        are written once. File *names* are copied rather than the FieldFile itself,
        because assigning a FieldFile would rebind it to the wrong field.
        """
        if not (self.about_video_file or self.about_video_url):
            return None
        return ProjectVideo(
            video_file=self.about_video_file.name if self.about_video_file else '',
            video_url=self.about_video_url or '',
            poster=self.about_video_poster.name if self.about_video_poster else '',
            orientation=self.about_video_orientation,
        )


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
    icon_image = models.ImageField(
        upload_to='tools/',
        blank=True,
        null=True,
        validators=[FileExtensionValidator(IMAGE_EXTENSIONS)],
        help_text='Optional logo picture. Leave it empty and the coloured letters are used instead.',
    )
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
