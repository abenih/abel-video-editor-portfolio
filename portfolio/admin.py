from django import forms
from django.contrib import admin
from django.shortcuts import redirect

from .models import (
    ExperienceEntry, Project, ProjectImage, ProjectVideo, SiteProfile, SkillGroup, SkillItem, Stat, Tool,
)


class ProjectImageInline(admin.TabularInline):
    model = ProjectImage
    extra = 1


class ProjectVideoInline(admin.TabularInline):
    model = ProjectVideo
    extra = 1


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'client', 'is_featured', 'order', 'created_at')
    list_filter = ('category', 'is_featured')
    search_fields = ('title', 'client', 'description')
    ordering = ('-is_featured', 'order', '-created_at')
    inlines = [ProjectVideoInline, ProjectImageInline]


@admin.register(SiteProfile)
class SiteProfileAdmin(admin.ModelAdmin):
    """A singleton 'Settings' page — clicking it in the sidebar jumps straight to the one editable form."""

    fieldsets = (
        ('Identity', {'fields': ('name', 'alias', 'title', 'tagline')}),
        ('About section', {'fields': ('bio', 'highlight', 'since')}),
        ('Hero copy', {'fields': ('availability_text', 'hero_primary_cta_label', 'hero_secondary_cta_label')}),
        ('Section visibility', {'fields': ('show_experience_section',)}),
        ('Theme colors', {
            'fields': (
                'theme_bg', 'theme_bg_alt', 'theme_text', 'theme_text_muted',
                'theme_accent', 'theme_accent_2', 'theme_accent_3',
            )
        }),
        ('Contact details', {'fields': ('location', 'phone', 'email')}),
        ('Social handles', {'fields': ('instagram', 'facebook', 'telegram')}),
        ('Homepage images', {
            'fields': (
                'hero_main_image', 'hero_badge_image', 'hero_cutout_image',
                'about_main_image', 'about_side_image',
            )
        }),
    )

    def has_add_permission(self, request):
        return not SiteProfile.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        profile = SiteProfile.load()
        return redirect('admin:portfolio_siteprofile_change', profile.pk)


@admin.register(Stat)
class StatAdmin(admin.ModelAdmin):
    list_display = ('value', 'label', 'icon', 'order')
    list_editable = ('order',)


class ToolAdminForm(forms.ModelForm):
    class Meta:
        model = Tool
        fields = '__all__'
        widgets = {
            'bg': forms.TextInput(attrs={'type': 'color'}),
            'fg': forms.TextInput(attrs={'type': 'color'}),
        }


@admin.register(Tool)
class ToolAdmin(admin.ModelAdmin):
    form = ToolAdminForm
    list_display = ('name', 'abbr', 'icon_image', 'order')
    list_editable = ('order',)


class SkillItemInline(admin.TabularInline):
    model = SkillItem
    extra = 1


@admin.register(SkillGroup)
class SkillGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'icon', 'order')
    list_editable = ('order',)
    inlines = [SkillItemInline]


@admin.register(ExperienceEntry)
class ExperienceEntryAdmin(admin.ModelAdmin):
    list_display = ('role', 'org', 'period', 'is_visible', 'order')
    list_editable = ('is_visible', 'order')
