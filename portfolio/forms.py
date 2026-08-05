from django import forms

from .models import ExperienceEntry, Project, SiteProfile, SkillGroup, SkillItem, Stat, Tool

MAX_VIDEO_SIZE_MB = 300


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
            'client': forms.TextInput(attrs={'placeholder': 'e.g. MTS Multimedia (optional)'}),
            'video_url': forms.URLInput(attrs={'placeholder': 'https://youtu.be/... (unlisted works great)'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style_fields()

    def clean_video_file(self):
        video_file = self.cleaned_data.get('video_file')
        if video_file and hasattr(video_file, 'size') and video_file.size > MAX_VIDEO_SIZE_MB * 1024 * 1024:
            raise forms.ValidationError(
                f'Keep uploaded files under {MAX_VIDEO_SIZE_MB}MB — use a YouTube/Vimeo link for longer videos.'
            )
        return video_file

    # Note: the "must provide a file or a link" rule lives on Project.clean()
    # so it also applies when editing projects via the Django admin.


class SiteProfileForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = SiteProfile
        fields = [
            'name', 'alias', 'title', 'tagline', 'bio', 'highlight', 'since',
            'location', 'phone', 'email', 'instagram', 'facebook', 'telegram',
        ]
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 5}),
            'highlight': forms.TextInput(attrs={'placeholder': 'Short pull-quote shown under the bio'}),
            'instagram': forms.TextInput(attrs={'placeholder': 'username (no @)'}),
            'facebook': forms.TextInput(attrs={'placeholder': 'username (no @)'}),
            'telegram': forms.TextInput(attrs={'placeholder': 'username (no @)'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style_fields()


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
        fields = ['name', 'abbr', 'bg', 'fg', 'order']
        widgets = {
            'abbr': forms.TextInput(attrs={'placeholder': 'e.g. Pr, Ae, Ps'}),
            'bg': forms.TextInput(attrs={'type': 'color'}),
            'fg': forms.TextInput(attrs={'type': 'color'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style_fields()


class ExperienceForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = ExperienceEntry
        fields = ['role', 'org', 'period', 'description', 'order']
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
