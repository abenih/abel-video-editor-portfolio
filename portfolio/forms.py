from urllib.parse import urlsplit

from django import forms
from django.core.validators import URLValidator

from .imaging import optimize_image
from .models import (
    ExperienceEntry, Project, ProjectImage, ProjectVideo, SiteProfile, SkillGroup, SkillItem, Stat, Tool,
    extract_tiktok_id, extract_vimeo_id, extract_youtube_id,
)

MAX_VIDEO_SIZE_MB = 300
MAX_IMAGE_SIZE_MB = 10
IMAGE_TOO_BIG = f'Keep pictures under {MAX_IMAGE_SIZE_MB}MB — resize it and upload it again.'
VIDEO_TOO_BIG = (
    f'Keep uploaded files under {MAX_VIDEO_SIZE_MB}MB — use a YouTube/Vimeo link for longer videos.'
)

# Matched label by label, so "evil-youtube.com" and "youtube.com.attacker.tld" both fail.
VIDEO_HOSTS = ('youtube.com', 'youtu.be', 'vimeo.com', 'tiktok.com')
WRONG_HOST = 'Paste a link from YouTube, Vimeo or TikTok — other websites can’t be played here.'
NO_VIDEO_ID = (
    'That link doesn’t point at one video. Open the video itself, then copy the address '
    'out of your browser’s address bar.'
)
TIKTOK_SHARE_LINK = (
    'That’s a TikTok share link. Open it in a browser, then copy the address bar — '
    'it should start with tiktok.com/@…'
)


def is_new_upload(value):
    """True only for a file the browser just posted.

    An unchanged row hands back the stored FieldFile instead, and reading its
    ``.size`` costs a disk hit per row — and raises if the file has gone missing
    from MEDIA_ROOT. Only real uploads carry ``content_type``.
    """
    return hasattr(value, 'content_type')


def _host_is_allowed(host):
    return any(host == domain or host.endswith('.' + domain) for domain in VIDEO_HOSTS)


def validate_video_url(url):
    """Allowlist the host, then insist a video id can be pulled out of the link.

    Nothing downstream ever embeds the pasted string: the id is what gets
    rebuilt into a player URL, so a link we cannot read an id from is useless
    and is rejected here rather than rendered as an empty frame.
    """
    if not url:
        return ''
    URLValidator(schemes=['http', 'https'])(url)
    host = (urlsplit(url).hostname or '').lower()
    if not _host_is_allowed(host):
        raise forms.ValidationError(WRONG_HOST)
    if extract_youtube_id(url) or extract_vimeo_id(url) or extract_tiktok_id(url):
        return url
    # Short links (vm.tiktok.com/…, tiktok.com/t/…) carry no id and cannot be
    # resolved without an outbound request, so they get their own instructions.
    raise forms.ValidationError(
        TIKTOK_SHARE_LINK if host == 'tiktok.com' or host.endswith('.tiktok.com') else NO_VIDEO_ID
    )


class StyledFormMixin:
    """Adds a consistent CSS class to every field's widget."""

    def _style_fields(self):
        for field in self.fields.values():
            css_class = 'form-checkbox' if isinstance(field.widget, forms.CheckboxInput) else 'form-input'
            existing = field.widget.attrs.get('class', '')
            field.widget.attrs['class'] = f'{existing} {css_class}'.strip()


class ProjectForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Project
        fields = [
            'title', 'category', 'client', 'description',
            'video_file', 'video_url', 'thumbnail', 'is_featured', 'order',
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4, 'placeholder': 'What was this project about?'}),
            'title': forms.TextInput(attrs={'placeholder': 'e.g. Sunset Wedding Highlight Reel'}),
            'category': forms.TextInput(attrs={'placeholder': 'e.g. Video Editing'}),
            'client': forms.TextInput(attrs={'placeholder': 'e.g. MTS Multimedia (optional)'}),
            'video_url': forms.URLInput(attrs={'placeholder': 'https://youtu.be/... (unlisted works great)'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Django's default URLValidator also accepts ftp/ftps, which no video host uses.
        self.fields['video_url'].validators = [URLValidator(schemes=['http', 'https'])]
        self._style_fields()

    def clean_video_file(self):
        video_file = self.cleaned_data.get('video_file')
        if is_new_upload(video_file) and video_file.size > MAX_VIDEO_SIZE_MB * 1024 * 1024:
            raise forms.ValidationError(VIDEO_TOO_BIG)
        return video_file

    # Note: the "must provide a file or a link" rule lives on Project.clean()
    # so it also applies when editing projects via the Django admin.


class ProjectImageForm(StyledFormMixin, forms.ModelForm):
    PREVIEW_KINDS = {'image': 'image'}

    class Meta:
        model = ProjectImage
        fields = ['image', 'order']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style_fields()

    def clean_image(self):
        image = self.cleaned_data.get('image')
        if is_new_upload(image) and image.size > MAX_IMAGE_SIZE_MB * 1024 * 1024:
            raise forms.ValidationError(IMAGE_TOO_BIG)
        return optimize_image(image) if is_new_upload(image) else image


ProjectImageFormSet = forms.inlineformset_factory(
    Project, ProjectImage, form=ProjectImageForm, extra=1, can_delete=True,
)


class ProjectVideoForm(StyledFormMixin, forms.ModelForm):
    # Tells the edit panel how to preview each file field — an .mp4 in an <img> is a broken image.
    PREVIEW_KINDS = {'video_file': 'video', 'poster': 'image'}

    class Meta:
        model = ProjectVideo
        fields = ['title', 'video_file', 'video_url', 'poster', 'orientation', 'is_cover', 'order']
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'e.g. Behind the scenes'}),
            'video_url': forms.URLInput(attrs={'placeholder': 'https://youtu.be/… or https://www.tiktok.com/@…'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['video_url'].validators = [URLValidator(schemes=['http', 'https'])]
        self._style_fields()

    def clean_video_file(self):
        video_file = self.cleaned_data.get('video_file')
        if is_new_upload(video_file) and video_file.size > MAX_VIDEO_SIZE_MB * 1024 * 1024:
            raise forms.ValidationError(VIDEO_TOO_BIG)
        return video_file

    def clean_poster(self):
        poster = self.cleaned_data.get('poster')
        if is_new_upload(poster) and poster.size > MAX_IMAGE_SIZE_MB * 1024 * 1024:
            raise forms.ValidationError(IMAGE_TOO_BIG)
        return poster

    def clean_video_url(self):
        return validate_video_url(self.cleaned_data.get('video_url'))

    def clean(self):
        cleaned = super().clean()
        has_file = bool(cleaned.get('video_file'))
        has_url = bool(cleaned.get('video_url'))
        if has_file and has_url:
            raise forms.ValidationError('Pick one — either upload the video or paste a link, not both.')
        if not has_file and not has_url and not self.errors:
            raise forms.ValidationError('Upload a video or paste a link.')
        return cleaned


ProjectVideoFormSet = forms.inlineformset_factory(
    Project, ProjectVideo, form=ProjectVideoForm, extra=1, can_delete=True,
)


class SiteProfileForm(StyledFormMixin, forms.ModelForm):
    IMAGE_FIELDS = (
        'hero_main_image', 'hero_badge_image', 'hero_cutout_image',
        'about_main_image', 'about_side_image', 'about_video_poster',
    )
    # Tells the edit panel how to preview each file field — an .mp4 in an <img> is a broken image.
    PREVIEW_KINDS = {'about_video_file': 'video'}

    class Meta:
        model = SiteProfile
        fields = [
            'name', 'alias', 'title', 'tagline', 'bio', 'highlight', 'since',
            'location', 'phone', 'email', 'instagram', 'facebook', 'telegram',
            'show_experience_section',
            'availability_text', 'hero_primary_cta_label', 'hero_secondary_cta_label',
            'theme_bg', 'theme_bg_alt', 'theme_text', 'theme_text_muted',
            'theme_accent', 'theme_accent_2', 'theme_accent_3',
            'hero_main_image', 'hero_badge_image', 'hero_cutout_image',
            'about_main_image', 'about_side_image',
            'about_video_file', 'about_video_url', 'about_video_poster', 'about_video_orientation',
        ]
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 5}),
            'highlight': forms.TextInput(attrs={'placeholder': 'Short pull-quote shown under the bio'}),
            'instagram': forms.TextInput(attrs={'placeholder': 'username (no @)'}),
            'facebook': forms.TextInput(attrs={'placeholder': 'username (no @)'}),
            'telegram': forms.TextInput(attrs={'placeholder': 'username (no @)'}),
            'availability_text': forms.TextInput(attrs={'placeholder': 'Available for freelance work'}),
            'hero_primary_cta_label': forms.TextInput(attrs={'placeholder': 'View My Work'}),
            'hero_secondary_cta_label': forms.TextInput(attrs={'placeholder': 'Get In Touch'}),
            'theme_bg': forms.TextInput(attrs={'type': 'color'}),
            'theme_bg_alt': forms.TextInput(attrs={'type': 'color'}),
            'theme_text': forms.TextInput(attrs={'type': 'color'}),
            'theme_text_muted': forms.TextInput(attrs={'type': 'color'}),
            'theme_accent': forms.TextInput(attrs={'type': 'color'}),
            'theme_accent_2': forms.TextInput(attrs={'type': 'color'}),
            'theme_accent_3': forms.TextInput(attrs={'type': 'color'}),
            'about_video_url': forms.URLInput(attrs={'placeholder': 'https://youtu.be/… or https://www.tiktok.com/@…'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'about_video_url' in self.fields:
            self.fields['about_video_url'].validators = [URLValidator(schemes=['http', 'https'])]
        self._style_fields()

    def clean_about_video_file(self):
        video_file = self.cleaned_data.get('about_video_file')
        if is_new_upload(video_file) and video_file.size > MAX_VIDEO_SIZE_MB * 1024 * 1024:
            raise forms.ValidationError(VIDEO_TOO_BIG)
        return video_file

    def clean_about_video_url(self):
        return validate_video_url(self.cleaned_data.get('about_video_url'))

    def clean(self):
        # Same cap as the gallery. Region forms only carry a subset of the fields.
        cleaned = super().clean()
        for name in self.IMAGE_FIELDS:
            value = cleaned.get(name)
            if is_new_upload(value) and value.size > MAX_IMAGE_SIZE_MB * 1024 * 1024:
                self.add_error(name, IMAGE_TOO_BIG)
            elif is_new_upload(value):
                cleaned[name] = optimize_image(value)
        if cleaned.get('about_video_file') and cleaned.get('about_video_url'):
            self.add_error(
                'about_video_url',
                'Pick one — either upload the video or paste a link, not both.',
            )
        return cleaned


class StatForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Stat
        fields = ['icon', 'value', 'label', 'order']
        widgets = {'value': forms.TextInput(attrs={'placeholder': 'e.g. 3+, 20+, 100%'})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style_fields()


class ToolForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Tool
        fields = ['name', 'abbr', 'icon_image', 'bg', 'fg', 'order']
        widgets = {
            'abbr': forms.TextInput(attrs={'placeholder': 'e.g. Pr, Ae, Ps'}),
            'bg': forms.TextInput(attrs={'type': 'color'}),
            'fg': forms.TextInput(attrs={'type': 'color'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style_fields()

    def clean_icon_image(self):
        icon_image = self.cleaned_data.get('icon_image')
        if is_new_upload(icon_image) and icon_image.size > MAX_IMAGE_SIZE_MB * 1024 * 1024:
            raise forms.ValidationError(IMAGE_TOO_BIG)
        # A logo never needs to be huge.
        return optimize_image(icon_image, max_edge=256) if is_new_upload(icon_image) else icon_image


class ExperienceForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = ExperienceEntry
        fields = ['role', 'org', 'period', 'description', 'is_visible', 'order']
        widgets = {
            'period': forms.TextInput(attrs={'placeholder': 'e.g. 2022 — Present'}),
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style_fields()


class SkillGroupForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = SkillGroup
        fields = ['name', 'icon', 'order']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style_fields()


class SkillItemForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = SkillItem
        fields = ['text', 'order']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style_fields()


SkillItemFormSet = forms.inlineformset_factory(
    SkillGroup, SkillItem, form=SkillItemForm, extra=1, can_delete=True,
)
