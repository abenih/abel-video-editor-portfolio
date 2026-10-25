"""Single source of truth for the click-to-edit regions on the public site.

Every editable part of the page is declared here once: which form builds it,
which model backs it, which subset of fields it owns, and the plain-language
wording the site owner sees. Views, URLs, the ``{% editable %}`` template tag
and the generic ``/manage/<key>/`` CRUD screens all read from this registry, so
adding a region is a single dict entry plus one template attribute.

Security note: nothing in here may ever be built from request data. Views look a
region up by key and use ``region.fields`` / ``region.model`` verbatim, which is
what keeps mass assignment and IDOR off the table.
"""
from dataclasses import dataclass, field

from django.forms import modelform_factory
from django.http import Http404

from .forms import (
    ExperienceForm, ProjectForm, ProjectImageFormSet, ProjectVideoFormSet, SiteProfileForm, SkillGroupForm,
    SkillItemFormSet, StatForm, ToolForm,
)
from .models import ExperienceEntry, Project, SiteProfile, SkillGroup, Stat, Tool


@dataclass(frozen=True)
class EditRegion:
    key: str
    """Stable slug — becomes the URL segment and the ``data-edit-key`` value."""

    label: str
    """Plain-language name, e.g. "The big text at the top"."""

    blurb: str
    """One line saying where this shows up on the page."""

    kind: str
    """``'profile'`` | ``'collection'`` | ``'nested'`` | ``'instance'``.

    ``'instance'`` edits one specific row whose pk the template supplies:
    ``{% editable 'project' project.pk %}``. The page decides *which* object,
    the registry still decides which model and which fields.
    """

    form_class: type | None
    model: type | None
    fields: tuple | None
    """Explicit field subset. Profile regions only — collections use their form's Meta."""

    fallback_url: str
    """URL name of the existing full manage screen, or '' when the panel page is the only one."""

    fallback_args: tuple
    anchor: str
    """DOM id on the home page to scroll back to after saving."""

    formset_class: type | None = None
    """Inline formset for ``kind='nested'`` and for instance regions that own child rows."""

    formset_label: str = 'Items'
    """Heading above the inline rows, e.g. "Bullet points"."""

    fallback_takes_pk: bool = False
    """True when fallback_url points at a per-object page and needs the instance pk."""

    field_labels: dict = field(default_factory=dict)
    """Plain-language label overrides. Model verbose_names stay developer-accurate."""

    field_help: dict = field(default_factory=dict)
    simple_content: bool = False
    """True when this region is also served by the generic ``/manage/<key>/`` CRUD views."""

    list_label: str = ''
    """Plural heading used by the existing manage screens, e.g. "Stats"."""

    singular: str = ''
    """Singular noun used in "Add …" buttons, e.g. "Stat"."""


PROFILE_REGIONS = (
    EditRegion(
        key='hero_text',
        label='The big text at the top',
        blurb='The headline, tagline and buttons visitors see first.',
        kind='profile',
        form_class=SiteProfileForm,
        model=None,
        fields=(
            'title', 'tagline', 'location', 'availability_text',
            'hero_primary_cta_label', 'hero_secondary_cta_label',
        ),
        fallback_url='portfolio:manage_profile',
        fallback_args=(),
        anchor='top',
        field_labels={
            'title': 'The big text at the top',
            'tagline': 'Your one-line summary',
            'location': "Where you're based",
            'availability_text': 'Are you taking on work?',
            'hero_primary_cta_label': 'Text on the first button',
            'hero_secondary_cta_label': 'Text on the second button',
        },
        field_help={
            'title': 'The first thing anyone reads, e.g. "Video Editor & Visual Storyteller".',
            'tagline': 'Sits just under the big text, and again at the bottom of every page.',
            'location': 'Shown in the small line above the big text, and in the footer.',
            'availability_text': 'The short status line next to your location, e.g. "Available for freelance work".',
            'hero_primary_cta_label': 'The filled button — it jumps down to your work.',
            'hero_secondary_cta_label': 'The outlined button — it jumps down to your contact details.',
        },
    ),
    EditRegion(
        key='hero_images',
        label='The photos at the top',
        blurb='The three pictures in the panel beside your headline.',
        kind='profile',
        form_class=SiteProfileForm,
        model=None,
        fields=('hero_main_image', 'hero_badge_image', 'hero_cutout_image'),
        fallback_url='portfolio:manage_profile',
        fallback_args=(),
        anchor='top',
        field_labels={
            'hero_main_image': 'Your main photo',
            'hero_badge_image': 'The small round photo',
            'hero_cutout_image': 'The cut-out photo behind it',
        },
        field_help={
            'hero_main_image': 'The large rounded portrait. Leave empty to keep the built-in picture.',
            'hero_badge_image': 'The little circle that overlaps the corner of the main photo.',
            'hero_cutout_image': 'Sits behind the main photo on the right-hand side.',
        },
    ),
    EditRegion(
        key='about_text',
        label='Your About Me words',
        blurb='The paragraph, the highlighted line and the year you started.',
        kind='profile',
        form_class=SiteProfileForm,
        model=None,
        fields=('bio', 'highlight', 'since'),
        fallback_url='portfolio:manage_profile',
        fallback_args=(),
        anchor='about',
        field_labels={
            'bio': 'Your About Me paragraph',
            'highlight': 'The line you want to stand out',
            'since': 'The year you started',
        },
        field_help={
            'bio': 'A few sentences about who you are and what you make.',
            'highlight': 'Shown as a short pull-quote directly under the paragraph.',
            'since': 'Just the year, e.g. 2021. It appears in the "Editing since …" chip.',
        },
    ),
    EditRegion(
        key='about_images',
        label='Your About Me photos',
        blurb='The pair of pictures under your About Me paragraph.',
        kind='profile',
        form_class=SiteProfileForm,
        model=None,
        fields=('about_main_image', 'about_side_image'),
        fallback_url='portfolio:manage_profile',
        fallback_args=(),
        anchor='about',
        field_labels={
            'about_main_image': 'The bigger photo',
            'about_side_image': 'The photo tucked behind it',
        },
        field_help={
            'about_main_image': 'The front picture of the pair. Leave empty to keep the built-in one.',
            'about_side_image': 'The picture peeking out from behind the first.',
        },
    ),
    EditRegion(
        key='about_video',
        label='The video beside your About Me',
        blurb='Plays in the panel next to your About Me words.',
        kind='profile',
        form_class=SiteProfileForm,
        model=None,
        fields=('about_video_file', 'about_video_url', 'about_video_poster', 'about_video_orientation'),
        fallback_url='portfolio:manage_profile',
        fallback_args=(),
        anchor='about',
        field_labels={
            'about_video_file': 'Upload a video',
            'about_video_url': 'Or paste a link',
            'about_video_poster': 'Picture shown before it plays',
            'about_video_orientation': 'What shape is it?',
        },
        field_help={
            'about_video_file': 'Leave both empty and the animated drawing stays.',
            'about_video_url': 'YouTube, Vimeo or TikTok — the full address.',
        },
    ),
    EditRegion(
        key='contact',
        label='How people reach you',
        blurb='The email, phone, location and social handles in the footer.',
        kind='profile',
        form_class=SiteProfileForm,
        model=None,
        fields=('email', 'phone', 'location', 'instagram', 'facebook', 'telegram'),
        fallback_url='portfolio:manage_profile',
        fallback_args=(),
        anchor='contact',
        field_labels={
            'email': 'Your email address',
            'phone': 'Your phone number',
            'location': "Where you're based",
            'instagram': 'Your Instagram username',
            'facebook': 'Your Facebook username',
            'telegram': 'Your Telegram username',
        },
        field_help={
            'email': 'Visitors can tap this to open their mail app.',
            'phone': 'Visitors can tap this to call you.',
            'location': 'Also shown in the small line at the very top of the page.',
            'instagram': 'Just the username — no @, no link, no spaces.',
            'facebook': 'Just the username — no @, no link, no spaces.',
            'telegram': 'Just the username — no @, no link, no spaces.',
        },
    ),
    EditRegion(
        key='identity',
        label='Your name',
        blurb='The name in the top bar, the footer and the browser tab.',
        kind='profile',
        form_class=SiteProfileForm,
        model=None,
        fields=('name', 'alias'),
        fallback_url='portfolio:manage_profile',
        fallback_args=(),
        anchor='top',
        field_labels={
            'name': 'Your full name',
            'alias': 'A shorter name for the top bar',
        },
        field_help={
            'name': 'Used in the footer, the copyright line and the browser tab title.',
            'alias': 'Optional. If you leave this empty the top bar shows your full name.',
        },
    ),
    EditRegion(
        key='theme',
        label='The site colours',
        blurb='Every colour used across the whole site.',
        kind='profile',
        form_class=SiteProfileForm,
        model=None,
        fields=(
            'theme_bg', 'theme_bg_alt', 'theme_text', 'theme_text_muted',
            'theme_accent', 'theme_accent_2', 'theme_accent_3',
        ),
        fallback_url='portfolio:manage_profile',
        fallback_args=(),
        anchor='top',
        field_labels={
            'theme_bg': 'Page background',
            'theme_bg_alt': 'Card background',
            'theme_text': 'Main text colour',
            'theme_text_muted': 'Quieter text colour',
            'theme_accent': 'Main highlight colour',
            'theme_accent_2': 'Second highlight colour',
            'theme_accent_3': 'Third highlight colour',
        },
        field_help={
            'theme_bg': 'The colour behind everything.',
            'theme_bg_alt': 'The slightly different background used on panels and cards.',
            'theme_text': 'Headings and important text.',
            'theme_text_muted': 'Body text and small print — keep it readable against the background.',
            'theme_accent': 'Buttons and links.',
            'theme_accent_2': 'Used in gradients and badges.',
            'theme_accent_3': 'Used for small accents like dates and ticks.',
        },
    ),
)

COLLECTION_REGIONS = (
    EditRegion(
        key='stats',
        label='The small numbers next to your photo',
        blurb='Small headline numbers shown in the hero, e.g. "3+ Years Editing".',
        kind='collection',
        form_class=StatForm,
        model=Stat,
        fields=None,
        fallback_url='portfolio:manage_content_list',
        fallback_args=('stats',),
        anchor='top',
        simple_content=True,
        list_label='Stats',
        singular='Stat',
        field_labels={
            'icon': 'Little picture',
            'value': 'The number',
            'label': 'What it means',
            'order': 'Position',
        },
        field_help={'order': 'Lower numbers show first.'},
    ),
    EditRegion(
        key='tools',
        label='The software you use',
        blurb='Software badges shown in the Tools & Skills section.',
        kind='collection',
        form_class=ToolForm,
        model=Tool,
        fields=None,
        fallback_url='portfolio:manage_content_list',
        fallback_args=('tools',),
        anchor='skills',
        simple_content=True,
        list_label='Tools',
        singular='Tool',
        field_labels={
            'name': 'Software name',
            'abbr': 'Short badge text',
            'icon_image': 'The logo picture',
            'bg': 'Badge background colour',
            'fg': 'Badge text colour',
            'order': 'Position',
        },
        field_help={
            'icon_image': 'A PNG or WEBP of the software logo. Leave it empty and the coloured letters are used instead.',
            'order': 'Lower numbers show first.',
        },
    ),
    EditRegion(
        key='experience',
        label='Your work history',
        blurb='Rows shown in the Experience timeline.',
        kind='collection',
        form_class=ExperienceForm,
        model=ExperienceEntry,
        fields=None,
        fallback_url='portfolio:manage_content_list',
        fallback_args=('experience',),
        anchor='experience',
        simple_content=True,
        list_label='Experience',
        singular='Experience entry',
        field_labels={
            'role': 'Job title',
            'org': 'Company or client',
            'period': 'When you did it',
            'description': 'What you did',
            'is_visible': 'Show this on the site',
            'order': 'Position',
        },
        field_help={'order': 'Lower numbers show first.'},
    ),
    EditRegion(
        key='projects',
        label='Your portfolio pieces',
        blurb='The cards in the Portfolio grid.',
        kind='collection',
        form_class=ProjectForm,
        model=Project,
        fields=None,
        fallback_url='portfolio:manage_projects',
        fallback_args=(),
        anchor='work',
        list_label='Projects',
        singular='Project',
        field_labels={
            'title': 'What is it called?',
            'category': 'What kind of work is it?',
            'client': 'Who was it for?',
            'description': 'What was the job?',
            'video_file': 'Upload the video',
            'video_url': 'Or paste a video link',
            'thumbnail': 'Cover picture',
            'is_featured': 'Show this one first',
            'order': 'Position',
        },
        field_help={
            'category': 'The small label under the title. Write whatever fits, e.g. "Video Editing".',
            'thumbnail': "The still image on the card. Leave it empty and the first video's picture is used.",
            'order': 'Lower numbers show first.',
        },
    ),
)

NESTED_REGIONS = (
    EditRegion(
        key='skills',
        label='Your skill lists',
        blurb='The cards of bullet points in the Tools & Skills section.',
        kind='nested',
        form_class=SkillGroupForm,
        model=SkillGroup,
        fields=None,
        fallback_url='portfolio:manage_skills',
        fallback_args=(),
        anchor='skills',
        formset_class=SkillItemFormSet,
        formset_label='Bullet points',
        list_label='Skills',
        singular='Skill group',
        field_labels={
            'name': 'Name of this group',
            'icon': 'Little picture',
            'order': 'Position',
        },
        field_help={'order': 'Lower numbers show first.'},
    ),
)

# Regions that edit one specific row, chosen by the page rather than by a list.
INSTANCE_REGIONS = (
    EditRegion(
        key='project',
        label='This piece of work',
        blurb='The name, type, client, video and cover picture on this page.',
        kind='instance',
        form_class=ProjectForm,
        model=Project,
        fields=None,
        fallback_url='portfolio:edit_project',
        fallback_args=(),
        fallback_takes_pk=True,
        anchor='work',
        list_label='Projects',
        singular='Project',
        field_labels={
            'title': 'What is it called?',
            'category': 'What kind of work is it?',
            'client': 'Who was it for?',
            'description': 'What was the job?',
            'video_file': 'Upload the video',
            'video_url': 'Or paste a video link',
            'thumbnail': 'Cover picture',
            'is_featured': 'Show this one first',
            'order': 'Position',
        },
        field_help={
            'category': 'The small label under the title. Write whatever fits, e.g. "Video Editing".',
            'thumbnail': "The still image on the card. Leave it empty and the first video's picture is used.",
            'order': 'Lower numbers show first.',
        },
    ),
    EditRegion(
        key='project_videos',
        label='The videos in this collection',
        blurb='Every video that plays inside this card.',
        kind='instance',
        form_class=None,
        model=Project,
        fields=None,
        # Like the gallery, this panel is the only place these rows can be edited.
        fallback_url='',
        fallback_args=(),
        anchor='work',
        formset_class=ProjectVideoFormSet,
        formset_label='Videos',
        list_label='Videos',
        singular='Video',
        field_labels={
            'title': 'Give it a name (optional)',
            'video_file': 'Upload the video',
            'video_url': 'Or paste a link',
            'poster': 'Picture shown before it plays',
            'orientation': 'What shape is it?',
            'is_cover': 'Use this one on the card',
            'order': 'Position',
        },
        field_help={
            'video_url': 'YouTube, Vimeo or TikTok. Paste the full address, not a short share link.',
            'orientation': 'Tall is for TikTok, Reels and Shorts. Wide is for normal videos.',
            'order': 'Lower numbers show first.',
        },
    ),
    EditRegion(
        key='project_gallery',
        label='The extra pictures on this page',
        blurb='The grid of extra shots shown under the video.',
        kind='instance',
        form_class=None,
        model=Project,
        fields=None,
        # This panel is the only place the gallery can be edited, so there is
        # no other "full editor" to point at.
        fallback_url='',
        fallback_args=(),
        anchor='work',
        formset_class=ProjectImageFormSet,
        formset_label='Pictures',
        list_label='Extra pictures',
        singular='Picture',
        field_labels={
            'image': 'Picture',
            'order': 'Position',
        },
        field_help={'order': 'Lower numbers show first.'},
    ),
)

EDIT_REGIONS: dict[str, EditRegion] = {
    region.key: region
    for region in (*PROFILE_REGIONS, *COLLECTION_REGIONS, *NESTED_REGIONS, *INSTANCE_REGIONS)
}


def get_region(key):
    """Look a region up by slug. Mirrors views._content_config — unknown key is a 404, never a crash."""
    region = EDIT_REGIONS.get(key)
    if not region:
        raise Http404(f'Unknown edit region "{key}".')
    return region


def _apply_wording(region, form):
    for name, label in region.field_labels.items():
        if name in form.fields:
            form.fields[name].label = label
    for name, help_text in region.field_help.items():
        if name in form.fields:
            form.fields[name].help_text = help_text
    return form


def build_form(region, instance=None, data=None, files=None):
    """Build the region's bound/unbound form, or None when the region is formset-only.

    Profile regions are narrowed with modelform_factory so they inherit
    StyledFormMixin, every widget (colour pickers included) and every help_text
    from SiteProfileForm while only exposing region.fields.
    """
    if region.form_class is None:
        return None
    if region.kind == 'profile':
        form_class = modelform_factory(SiteProfile, form=SiteProfileForm, fields=list(region.fields))
        instance = SiteProfile.load()
    else:
        form_class = region.form_class
    return _apply_wording(region, form_class(data=data, files=files, instance=instance))


def build_formset(region, instance=None, data=None, files=None):
    """Inline formset for regions that own child rows, or None."""
    if not region.formset_class:
        return None
    formset = region.formset_class(data=data, files=files, instance=instance)
    for form in formset.forms:
        _apply_wording(region, form)
    return formset
