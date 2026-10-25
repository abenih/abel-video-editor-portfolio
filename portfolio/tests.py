import io
import os
import re
import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import resolve, reverse

from . import views
from .editing import EDIT_REGIONS, build_form
from .forms import MAX_IMAGE_SIZE_MB, ProjectImageForm, validate_video_url
from .models import (
    ExperienceEntry, Project, ProjectImage, ProjectVideo, SiteProfile, SkillGroup, Stat, Tool,
)

# The project ships a WhiteNoise manifest storage; tests run with DEBUG=False, so
# {% static %} would demand a freshly collected manifest for the new editor assets.
# Swap in the plain backend so the suite does not depend on `collectstatic` first.
TEST_STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
}

# Gallery uploads are real files, so they need somewhere disposable to land.
TEST_MEDIA_ROOT = tempfile.mkdtemp(prefix='portfolio-test-media-')


def png_upload(name='shot.png'):
    """A real 1x1 PNG, so ImageField's Pillow check passes like it does in the browser."""
    from PIL import Image

    buffer = io.BytesIO()
    Image.new('RGB', (1, 1), '#123456').save(buffer, format='PNG')
    return SimpleUploadedFile(name, buffer.getvalue(), content_type='image/png')


@override_settings(STORAGES=TEST_STORAGES)
class PanelTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.staff = User.objects.create_user('panel_staff', password='pw-staff-1234', is_staff=True)
        cls.visitor = User.objects.create_user('panel_visitor', password='pw-visitor-1234')
        profile = SiteProfile.load()
        profile.name = 'Original Name'
        profile.title = 'Original Title'
        profile.tagline = 'Original tagline'
        profile.save()
        cls.stat = Stat.objects.create(icon='check', value='3+', label='Years', order=0)

    def login_staff(self):
        self.client.force_login(self.staff)


class PanelAccessTests(PanelTestCase):
    def test_anonymous_is_redirected_to_login(self):
        response = self.client.get(reverse('portfolio:edit_panel', args=['hero_text']))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse('portfolio:login')))

    def test_logged_in_non_staff_is_forbidden(self):
        self.client.force_login(self.visitor)
        response = self.client.get(reverse('portfolio:edit_panel', args=['hero_text']))
        self.assertEqual(response.status_code, 403)

    def test_staff_gets_the_panel(self):
        self.login_staff()
        response = self.client.get(reverse('portfolio:edit_panel', args=['hero_text']))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="title"')
        self.assertContains(response, 'name="csrfmiddlewaretoken"')

    def test_unknown_key_is_404(self):
        self.login_staff()
        self.assertEqual(self.client.get('/manage/edit/not_a_region/').status_code, 404)

    def test_a_pk_on_a_region_that_has_no_list_is_404(self):
        """Profile regions edit the one settings row, so an item id is a bad URL, not a crash."""
        self.login_staff()
        self.assertEqual(self.client.get('/manage/edit/hero_text/1/').status_code, 404)

    def test_delete_unknown_key_is_404(self):
        self.login_staff()
        response = self.client.post(f'/manage/edit/not_a_region/{self.stat.pk}/delete/')
        self.assertEqual(response.status_code, 404)

    def test_delete_is_post_only(self):
        self.login_staff()
        url = reverse('portfolio:edit_panel_delete', args=['stats', self.stat.pk])
        self.assertEqual(self.client.get(url).status_code, 405)

    def test_delete_requires_staff(self):
        self.client.force_login(self.visitor)
        url = reverse('portfolio:edit_panel_delete', args=['stats', self.stat.pk])
        self.assertEqual(self.client.post(url).status_code, 403)
        self.assertTrue(Stat.objects.filter(pk=self.stat.pk).exists())

    def test_post_without_csrf_token_is_forbidden(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.staff)
        response = csrf_client.post(
            reverse('portfolio:edit_panel', args=['hero_text']),
            {'title': 'Hijacked', 'tagline': 'x', 'location': '', 'availability_text': '',
             'hero_primary_cta_label': 'a', 'hero_secondary_cta_label': 'b'},
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(SiteProfile.load().title, 'Original Title')

    def test_panel_page_is_never_cached(self):
        self.login_staff()
        response = self.client.get(reverse('portfolio:edit_panel', args=['hero_text']))
        self.assertIn('no-store', response['Cache-Control'])

    def test_every_region_renders_for_staff(self):
        self.login_staff()
        Tool.objects.create(name='Premiere', abbr='Pr', order=0)
        ExperienceEntry.objects.create(role='Editor', period='2022 — Present', order=0)
        SkillGroup.objects.create(name='Editing', icon='video', order=0)
        project = Project.objects.create(title='Reel', category='video', video_url='https://youtu.be/abc123')
        for key, region in EDIT_REGIONS.items():
            with self.subTest(key=key):
                url = (
                    reverse('portfolio:edit_panel_item', args=[key, project.pk])
                    if region.kind == 'instance'
                    else reverse('portfolio:edit_panel', args=[key])
                )
                self.assertEqual(self.client.get(url).status_code, 200)


class PanelSaveTests(PanelTestCase):
    def test_profile_region_saves_and_redirects_to_the_anchor(self):
        self.login_staff()
        response = self.client.post(reverse('portfolio:edit_panel', args=['hero_text']), {
            'title': 'New Headline',
            'tagline': 'New tagline',
            'location': 'Addis Ababa',
            'availability_text': 'Open for work',
            'hero_primary_cta_label': 'See work',
            'hero_secondary_cta_label': 'Say hello',
        })
        self.assertRedirects(response, '/#top', fetch_redirect_response=False)
        self.assertEqual(SiteProfile.load().title, 'New Headline')

    def test_profile_region_cannot_touch_fields_outside_its_subset(self):
        self.login_staff()
        self.client.post(reverse('portfolio:edit_panel', args=['hero_text']), {
            'title': 'New Headline',
            'tagline': 'New tagline',
            'location': '',
            'availability_text': '',
            'hero_primary_cta_label': 'a',
            'hero_secondary_cta_label': 'b',
            'name': 'Mass Assigned',
            'email': 'attacker@example.com',
            'theme_bg': '#ff0000',
        })
        profile = SiteProfile.load()
        self.assertEqual(profile.name, 'Original Name')
        self.assertEqual(profile.email, '')
        self.assertEqual(profile.theme_bg, '#08080c')

    def test_profile_picture_over_the_size_cap_is_rejected(self):
        """Profile photos get the same cap as gallery pictures."""
        upload = png_upload('huge.png')
        upload.size = (MAX_IMAGE_SIZE_MB + 1) * 1024 * 1024
        form = build_form(EDIT_REGIONS['hero_images'], data={}, files={'hero_main_image': upload})
        self.assertFalse(form.is_valid())
        self.assertIn('hero_main_image', form.errors)

    def test_collection_item_saves(self):
        self.login_staff()
        response = self.client.post(
            reverse('portfolio:edit_panel_item', args=['stats', self.stat.pk]),
            {'icon': 'clock', 'value': '9+', 'label': 'Years editing', 'order': '1'},
        )
        self.assertEqual(response.status_code, 302)
        self.stat.refresh_from_db()
        self.assertEqual(self.stat.value, '9+')

    def test_collection_new_item_is_created(self):
        self.login_staff()
        response = self.client.post(
            reverse('portfolio:edit_panel_new', args=['stats']),
            {'icon': 'check', 'value': '40+', 'label': 'Clients', 'order': '2'},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Stat.objects.filter(label='Clients').exists())

    def test_invalid_post_redisplays_the_form(self):
        self.login_staff()
        response = self.client.post(
            reverse('portfolio:edit_panel_item', args=['stats', self.stat.pk]),
            {'icon': 'check', 'value': '', 'label': '', 'order': '0'},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'This field is required.')

    def test_delete_removes_the_item(self):
        self.login_staff()
        url = reverse('portfolio:edit_panel_delete', args=['stats', self.stat.pk])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Stat.objects.filter(pk=self.stat.pk).exists())

    def test_profile_regions_cannot_be_deleted(self):
        self.login_staff()
        response = self.client.post('/manage/edit/hero_text/1/delete/')
        self.assertEqual(response.status_code, 404)

    def test_offsite_next_is_ignored(self):
        self.login_staff()
        response = self.client.post(
            reverse('portfolio:edit_panel_item', args=['stats', self.stat.pk]),
            {'icon': 'check', 'value': '3+', 'label': 'Years', 'order': '0',
             'next': 'https://evil.example.com/'},
        )
        self.assertRedirects(response, '/#top', fetch_redirect_response=False)

    def test_panel_header_returns_a_bare_fragment(self):
        self.login_staff()
        response = self.client.get(
            reverse('portfolio:edit_panel', args=['hero_text']), headers={'x-panel': '1'},
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, '<body')
        self.assertContains(response, 'data-panel-key="hero_text"')


class InstanceRegionTests(PanelTestCase):
    """Regions that edit the one row the page is showing, e.g. {% editable 'project' project.pk %}."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.project = Project.objects.create(
            title='Original Reel', category='video', video_url='https://youtu.be/abc123',
        )
        cls.other = Project.objects.create(
            title='Other Reel', category='design', video_url='https://youtu.be/def456',
        )

    def panel_url(self, key, pk=None):
        return reverse('portfolio:edit_panel_item', args=[key, pk or self.project.pk])

    def test_anonymous_is_redirected_to_login(self):
        for key in ('project', 'project_gallery'):
            with self.subTest(key=key):
                response = self.client.get(self.panel_url(key))
                self.assertEqual(response.status_code, 302)
                self.assertTrue(response.url.startswith(reverse('portfolio:login')))

    def test_logged_in_non_staff_is_forbidden(self):
        self.client.force_login(self.visitor)
        for key in ('project', 'project_gallery'):
            with self.subTest(key=key):
                self.assertEqual(self.client.get(self.panel_url(key)).status_code, 403)

    def test_unknown_key_is_404(self):
        self.login_staff()
        self.assertEqual(self.client.get(f'/manage/edit/not_a_region/{self.project.pk}/').status_code, 404)

    def test_staff_gets_the_panel(self):
        self.login_staff()
        response = self.client.get(self.panel_url('project'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="title"')
        self.assertContains(response, 'value="Original Reel"')
        self.assertContains(response, 'name="csrfmiddlewaretoken"')

    def test_gallery_panel_renders_the_inline_formset(self):
        self.login_staff()
        response = self.client.get(self.panel_url('project_gallery'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="gallery-TOTAL_FORMS"')
        self.assertContains(response, 'name="gallery-0-image"')

    def test_missing_pk_is_404(self):
        self.login_staff()
        for key in ('project', 'project_gallery'):
            with self.subTest(key=key):
                self.assertEqual(self.client.get(f'/manage/edit/{key}/').status_code, 404)

    def test_pk_that_does_not_exist_is_404(self):
        self.login_staff()
        self.assertEqual(self.client.get(self.panel_url('project', pk=99999)).status_code, 404)

    def test_instance_regions_cannot_be_deleted_through_the_panel(self):
        self.login_staff()
        url = reverse('portfolio:edit_panel_delete', args=['project', self.project.pk])
        self.assertEqual(self.client.post(url).status_code, 404)
        self.assertTrue(Project.objects.filter(pk=self.project.pk).exists())

    def test_saving_edits_only_the_project_on_the_page(self):
        self.login_staff()
        response = self.client.post(self.panel_url('project'), {
            'title': 'Renamed Reel',
            'category': 'video',
            'client': '',
            'description': '',
            'video_url': 'https://youtu.be/abc123',
            'order': '0',
        })
        self.assertRedirects(response, f'/project/{self.project.pk}/', fetch_redirect_response=False)
        self.project.refresh_from_db()
        self.other.refresh_from_db()
        self.assertEqual(self.project.title, 'Renamed Reel')
        self.assertEqual(self.other.title, 'Other Reel')

    def test_offsite_next_is_ignored(self):
        self.login_staff()
        response = self.client.post(self.panel_url('project'), {
            'title': 'Renamed Reel', 'category': 'video', 'client': '', 'description': '',
            'video_url': 'https://youtu.be/abc123', 'order': '0',
            'next': 'https://evil.example.com/',
        })
        self.assertRedirects(response, f'/project/{self.project.pk}/', fetch_redirect_response=False)


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class GalleryFormsetTests(PanelTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.addClassCleanup(shutil.rmtree, TEST_MEDIA_ROOT, True)

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.project = Project.objects.create(
            title='Gallery Reel', category='design', video_url='https://youtu.be/abc123',
        )

    def gallery_url(self):
        return reverse('portfolio:edit_panel_item', args=['project_gallery', self.project.pk])

    def add_shot(self, order=0):
        return ProjectImage.objects.create(project=self.project, image=png_upload(), order=order)

    def test_adding_a_picture_persists(self):
        self.login_staff()
        response = self.client.post(self.gallery_url(), {
            'gallery-TOTAL_FORMS': '1',
            'gallery-INITIAL_FORMS': '0',
            'gallery-MIN_NUM_FORMS': '0',
            'gallery-MAX_NUM_FORMS': '1000',
            'gallery-0-id': '',
            'gallery-0-order': '0',
            'gallery-0-image': png_upload('added.png'),
        })
        self.assertRedirects(response, f'/project/{self.project.pk}/', fetch_redirect_response=False)
        self.assertEqual(self.project.gallery.count(), 1)

    def test_removing_a_picture_persists(self):
        shot = self.add_shot()
        self.login_staff()
        response = self.client.post(self.gallery_url(), {
            'gallery-TOTAL_FORMS': '1',
            'gallery-INITIAL_FORMS': '1',
            'gallery-MIN_NUM_FORMS': '0',
            'gallery-MAX_NUM_FORMS': '1000',
            'gallery-0-id': str(shot.pk),
            'gallery-0-order': '0',
            'gallery-0-DELETE': 'on',
        })
        self.assertEqual(response.status_code, 302)
        self.assertFalse(ProjectImage.objects.filter(pk=shot.pk).exists())

    def test_one_post_can_add_and_remove_at_once(self):
        shot = self.add_shot()
        self.login_staff()
        response = self.client.post(self.gallery_url(), {
            'gallery-TOTAL_FORMS': '2',
            'gallery-INITIAL_FORMS': '1',
            'gallery-MIN_NUM_FORMS': '0',
            'gallery-MAX_NUM_FORMS': '1000',
            'gallery-0-id': str(shot.pk),
            'gallery-0-order': '0',
            'gallery-0-DELETE': 'on',
            'gallery-1-id': '',
            'gallery-1-order': '1',
            'gallery-1-image': png_upload('replacement.png'),
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.project.gallery.count(), 1)
        self.assertNotEqual(self.project.gallery.first().pk, shot.pk)

    def test_pictures_cannot_be_attached_to_another_project(self):
        """The parent comes from the URL — a forged FK in the POST must not move rows."""
        victim = Project.objects.create(title='Victim', category='video', video_url='https://youtu.be/zzz999')
        self.login_staff()
        self.client.post(self.gallery_url(), {
            'gallery-TOTAL_FORMS': '1',
            'gallery-INITIAL_FORMS': '0',
            'gallery-MIN_NUM_FORMS': '0',
            'gallery-MAX_NUM_FORMS': '1000',
            'gallery-0-id': '',
            'gallery-0-project': str(victim.pk),
            'gallery-0-order': '0',
            'gallery-0-image': png_upload('sneaky.png'),
        })
        self.assertEqual(victim.gallery.count(), 0)
        self.assertFalse(ProjectImage.objects.exclude(project=self.project).exists())

    def test_size_cap_rejects_an_oversized_picture(self):
        upload = png_upload('huge.png')
        upload.size = (MAX_IMAGE_SIZE_MB + 1) * 1024 * 1024
        form = ProjectImageForm(data={'order': '0'}, files={'image': upload})
        self.assertFalse(form.is_valid())
        self.assertIn('image', form.errors)

    def test_a_row_whose_file_is_missing_from_disk_still_saves(self):
        """Untouched rows must never be re-measured: the size check is for new uploads only."""
        shot = self.add_shot()
        os.remove(shot.image.path)
        self.login_staff()
        response = self.client.post(self.gallery_url(), {
            'gallery-TOTAL_FORMS': '1',
            'gallery-INITIAL_FORMS': '1',
            'gallery-MIN_NUM_FORMS': '0',
            'gallery-MAX_NUM_FORMS': '1000',
            'gallery-0-id': str(shot.pk),
            'gallery-0-order': '4',
        })
        self.assertEqual(response.status_code, 302)
        shot.refresh_from_db()
        self.assertEqual(shot.order, 4)


class EditableMarkupTests(PanelTestCase):
    def test_public_home_has_no_edit_markup_or_editor_assets(self):
        body = self.client.get(reverse('portfolio:home')).content.decode()
        self.assertNotIn('data-edit-key', body)
        self.assertNotIn('editor.js', body)
        self.assertNotIn('editor.css', body)
        self.assertNotIn('editModeToggle', body)

    def test_non_staff_home_has_no_edit_markup(self):
        self.client.force_login(self.visitor)
        body = self.client.get(reverse('portfolio:home')).content.decode()
        self.assertNotIn('data-edit-key', body)
        self.assertNotIn('editor.js', body)

    def test_staff_home_marks_every_on_page_region(self):
        Project.objects.create(title='Reel', category='video', video_url='https://youtu.be/abc123')
        self.login_staff()
        body = self.client.get(reverse('portfolio:home')).content.decode()
        for key in ('hero_text', 'hero_images', 'stats', 'about_text', 'about_images',
                    'tools', 'skills', 'projects', 'contact'):
            with self.subTest(key=key):
                self.assertIn(f'data-edit-key="{key}"', body)
        self.assertIn('editor.js', body)
        self.assertIn('editor.css', body)
        self.assertIn('id="editModeToggle"', body)

    def test_experience_region_is_marked_when_the_section_shows(self):
        ExperienceEntry.objects.create(role='Editor', period='2022 — Present', order=0)
        self.login_staff()
        body = self.client.get(reverse('portfolio:home')).content.decode()
        self.assertIn('data-edit-key="experience"', body)

    def test_the_top_bar_marks_the_name_and_the_colours(self):
        self.login_staff()
        body = self.client.get(reverse('portfolio:home')).content.decode()
        self.assertIn('data-edit-key="identity"', body)
        self.assertIn('data-edit-key="theme"', body)
        self.assertIn(reverse('portfolio:edit_panel', args=['theme']), body)

    def test_staff_project_page_marks_the_project_and_its_gallery(self):
        project = Project.objects.create(title='Reel', category='video', video_url='https://youtu.be/abc123')
        self.login_staff()
        body = self.client.get(project.get_absolute_url()).content.decode()
        for key in ('project', 'project_gallery', 'identity', 'theme', 'contact'):
            with self.subTest(key=key):
                self.assertIn(f'data-edit-key="{key}"', body)
        self.assertIn(f'data-edit-pk="{project.pk}"', body)

    def test_public_project_page_has_no_edit_markup(self):
        project = Project.objects.create(title='Reel', category='video', video_url='https://youtu.be/abc123')
        body = self.client.get(project.get_absolute_url()).content.decode()
        self.assertNotIn('data-edit-key', body)
        self.assertNotIn('data-edit-pk', body)
        self.assertNotIn('editor.js', body)

    def test_non_staff_project_page_has_no_edit_markup(self):
        project = Project.objects.create(title='Reel', category='video', video_url='https://youtu.be/abc123')
        self.client.force_login(self.visitor)
        body = self.client.get(project.get_absolute_url()).content.decode()
        self.assertNotIn('data-edit-key', body)
        self.assertNotIn('data-edit-pk', body)

    def test_every_region_is_reachable_from_a_real_page(self):
        """The registry must not grow a region with nowhere to click it."""
        Project.objects.create(title='Reel', category='video', video_url='https://youtu.be/abc123')
        Tool.objects.create(name='Premiere', abbr='Pr', order=0)
        ExperienceEntry.objects.create(role='Editor', period='2022 — Present', order=0)
        SkillGroup.objects.create(name='Editing', icon='video', order=0)
        self.login_staff()

        seen = set()
        for path in (reverse('portfolio:home'), Project.objects.first().get_absolute_url()):
            body = self.client.get(path).content.decode()
            seen.update(re.findall(r'data-edit-key="([^"]+)"', body))
        self.assertEqual(sorted(seen), sorted(EDIT_REGIONS))


class UrlOrderingRegressionTests(PanelTestCase):
    def test_generic_manage_routes_are_not_shadowed(self):
        self.assertIs(resolve('/manage/stats/').func, views.manage_content_list)
        self.assertEqual(resolve('/manage/stats/').kwargs['key'], 'stats')
        self.assertIs(resolve('/manage/tools/').func, views.manage_content_list)
        self.assertIs(resolve('/manage/experience/').func, views.manage_content_list)
        self.assertIs(resolve('/manage/stats/add/').func, views.manage_content_edit)
        self.assertIs(resolve('/manage/stats/1/edit/').func, views.manage_content_edit)
        self.assertIs(resolve('/manage/stats/1/delete/').func, views.manage_content_delete)

    def test_specific_manage_routes_are_not_shadowed(self):
        self.assertIs(resolve('/manage/profile/').func, views.manage_profile)
        self.assertIs(resolve('/manage/skills/').func, views.manage_skills)
        self.assertIs(resolve('/manage/skills/add/').func, views.manage_skill_add)

    def test_panel_routes_win_over_the_generic_block(self):
        self.assertIs(resolve('/manage/edit/hero_text/').func, views.edit_panel)
        self.assertIs(resolve('/manage/edit/stats/1/').func, views.edit_panel)
        self.assertIs(resolve('/manage/edit/stats/1/delete/').func, views.edit_panel_delete)

    def test_existing_manage_pages_still_render(self):
        self.login_staff()
        for url in ('/manage/stats/', '/manage/tools/', '/manage/experience/',
                    '/manage/profile/', '/manage/skills/'):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)


class SimpleContentRegistryTests(PanelTestCase):
    def test_simple_content_still_exposes_the_original_three_keys(self):
        self.assertEqual(set(views.SIMPLE_CONTENT), {'stats', 'tools', 'experience'})
        self.assertEqual(views.SIMPLE_CONTENT['experience']['singular'], 'Experience entry')
        self.assertEqual(views.SIMPLE_CONTENT['stats']['label'], 'Stats')
        self.assertIs(views.SIMPLE_CONTENT['tools']['model'], Tool)


class VideoUrlValidationTests(TestCase):
    """A pasted link is never embedded as-is, so anything we cannot read an id from is rejected."""

    def test_the_three_supported_hosts_are_accepted(self):
        for url in (
            'https://www.youtube.com/watch?v=eRsGyueVLvQ',
            'https://youtu.be/eRsGyueVLvQ',
            'https://vimeo.com/76979871',
            'https://www.tiktok.com/@someone/video/7123456789012345678',
        ):
            with self.subTest(url=url):
                self.assertEqual(validate_video_url(url), url)

    def test_lookalike_host_is_rejected(self):
        """`endswith` alone would let evil-youtube.com through; the label boundary stops it."""
        for url in (
            'https://evil-youtube.com/watch?v=eRsGyueVLvQ',
            'https://youtube.com.attacker.tld/watch?v=eRsGyueVLvQ',
        ):
            with self.subTest(url=url):
                with self.assertRaises(ValidationError):
                    validate_video_url(url)

    def test_unsupported_host_is_rejected(self):
        with self.assertRaises(ValidationError):
            validate_video_url('https://example.com/video.mp4')

    def test_non_http_scheme_is_rejected(self):
        with self.assertRaises(ValidationError):
            validate_video_url('ftp://youtube.com/watch?v=eRsGyueVLvQ')

    def test_tiktok_short_link_gets_its_own_instructions(self):
        for url in ('https://vm.tiktok.com/ZMabcdefg/', 'https://www.tiktok.com/t/ZTabcdefg/'):
            with self.subTest(url=url):
                with self.assertRaises(ValidationError) as caught:
                    validate_video_url(url)
                self.assertIn('share link', ' '.join(caught.exception.messages))


@override_settings(STORAGES=TEST_STORAGES, MEDIA_ROOT=TEST_MEDIA_ROOT)
class VideoFormsetTests(PanelTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.addClassCleanup(shutil.rmtree, TEST_MEDIA_ROOT, True)

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.project = Project.objects.create(title='Collection', category='Video Editing',
                                             thumbnail=png_upload('cover.png'))

    def videos_url(self):
        return reverse('portfolio:edit_panel_item', args=['project_videos', self.project.pk])

    def payload(self, **overrides):
        data = {
            'videos-TOTAL_FORMS': '1',
            'videos-INITIAL_FORMS': '0',
            'videos-MIN_NUM_FORMS': '0',
            'videos-MAX_NUM_FORMS': '1000',
            'videos-0-id': '',
            'videos-0-title': '',
            'videos-0-video_url': 'https://youtu.be/eRsGyueVLvQ',
            'videos-0-orientation': 'landscape',
            'videos-0-order': '0',
        }
        data.update(overrides)
        return data

    def test_adding_a_video_persists(self):
        self.login_staff()
        response = self.client.post(self.videos_url(), self.payload())
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.project.videos.count(), 1)

    def test_removing_a_video_persists(self):
        video = ProjectVideo.objects.create(project=self.project, video_url='https://youtu.be/eRsGyueVLvQ')
        self.login_staff()
        response = self.client.post(self.videos_url(), self.payload(**{
            'videos-INITIAL_FORMS': '1',
            'videos-0-id': str(video.pk),
            'videos-0-DELETE': 'on',
        }))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(ProjectVideo.objects.filter(pk=video.pk).exists())

    def test_one_post_can_add_and_remove_at_once(self):
        video = ProjectVideo.objects.create(project=self.project, video_url='https://youtu.be/eRsGyueVLvQ')
        self.login_staff()
        response = self.client.post(self.videos_url(), self.payload(**{
            'videos-TOTAL_FORMS': '2',
            'videos-INITIAL_FORMS': '1',
            'videos-0-id': str(video.pk),
            'videos-0-DELETE': 'on',
            'videos-1-id': '',
            'videos-1-title': '',
            'videos-1-video_url': 'https://vimeo.com/76979871',
            'videos-1-orientation': 'portrait',
            'videos-1-order': '1',
        }))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.project.videos.count(), 1)
        self.assertNotEqual(self.project.videos.first().pk, video.pk)

    def test_videos_cannot_be_attached_to_another_project(self):
        """The parent comes from the URL. Django rejects a mismatched FK outright, so a
        forged `project` saves nothing at all rather than quietly landing on the victim."""
        victim = Project.objects.create(title='Victim', category='Video Editing',
                                        thumbnail=png_upload('victim.png'))
        self.login_staff()
        response = self.client.post(self.videos_url(), self.payload(**{'videos-0-project': str(victim.pk)}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(victim.videos.count(), 0)
        self.assertEqual(self.project.videos.count(), 0)

    def test_a_bad_link_is_rejected_and_nothing_is_saved(self):
        self.login_staff()
        response = self.client.post(self.videos_url(),
                                    self.payload(**{'videos-0-video_url': 'https://evil-youtube.com/watch?v=x'}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.project.videos.count(), 0)

    def test_anonymous_cannot_reach_the_panel(self):
        self.assertEqual(self.client.get(self.videos_url()).status_code, 302)

    def test_non_staff_cannot_reach_the_panel(self):
        self.client.force_login(self.visitor)
        self.assertEqual(self.client.get(self.videos_url()).status_code, 403)


class CategoryIsFreeTextTests(TestCase):
    """Categories became the owner's own words, so anything he types must survive a round trip."""

    def test_arbitrary_label_is_stored_verbatim(self):
        project = Project.objects.create(title='Anything', category='Wedding Films & Reels',
                                         video_url='https://youtu.be/eRsGyueVLvQ')
        project.full_clean(exclude=['slug'])
        project.refresh_from_db()
        self.assertEqual(project.category, 'Wedding Films & Reels')


@override_settings(STORAGES=TEST_STORAGES, MEDIA_ROOT=TEST_MEDIA_ROOT)
class ProjectValidationTests(TestCase):
    """Design/graphic pieces carry a cover picture instead of a video, and must still save."""

    def test_cover_picture_alone_is_enough(self):
        project = Project(
            title='Cover art only',
            category='design',
            description='An image-only piece.',
            thumbnail=png_upload('cover.png'),
        )
        project.full_clean()

    def test_video_link_alone_is_enough(self):
        project = Project(
            title='Link only',
            category='video',
            description='A video-only piece.',
            video_url='https://www.youtube.com/watch?v=jNQXAC9IVRw',
        )
        project.full_clean()

    def test_a_piece_with_no_video_and_no_picture_is_rejected(self):
        project = Project(title='Nothing', category='video', description='No media at all.')
        with self.assertRaises(ValidationError):
            project.full_clean()

