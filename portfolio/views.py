from functools import wraps

from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import (
    ExperienceForm, ProjectForm, SiteProfileForm, SkillGroupForm, SkillItemFormSet, StatForm, ToolForm,
)
from .models import ExperienceEntry, Project, SiteProfile, SkillGroup, Stat, Tool

from .forms import ProjectForm
from .models import ExperienceEntry, Project, SkillGroup, Stat, Tool


def owner_required(view_func):
    """Redirects anonymous users to login; blocks logged-in non-staff users with 403."""
    @wraps(view_func)
    @login_required(login_url='portfolio:login')
    def wrapper(request, *args, **kwargs):
        if not request.user.is_staff:
            raise PermissionDenied('You do not have permission to manage portfolio projects.')
        return view_func(request, *args, **kwargs)
    return wrapper


def home(request):
    context = {
        'stats': Stat.objects.all(),
        'tools': Tool.objects.all(),
        'skills': SkillGroup.objects.prefetch_related('items').all(),
        'experience': ExperienceEntry.objects.filter(is_visible=True),
        'projects': Project.objects.all(),
        'categories': Project.CATEGORY_CHOICES,
    }
    return render(request, 'portfolio/home.html', context)


def project_detail(request, pk):
    project = get_object_or_404(Project, pk=pk)
    return render(request, 'portfolio/project_detail.html', {'project': project})


@owner_required
def upload_project(request):
    if request.method == 'POST':
        form = ProjectForm(request.POST, request.FILES)
        if form.is_valid():
            project = form.save()
            messages.success(request, f'"{project.title}" was added to your portfolio.')
            return redirect('portfolio:project_detail', pk=project.pk)
    else:
        form = ProjectForm()
    return render(request, 'portfolio/project_form.html', {'form': form, 'mode': 'add'})


@owner_required
def edit_project(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if request.method == 'POST':
        form = ProjectForm(request.POST, request.FILES, instance=project)
        if form.is_valid():
            form.save()
            messages.success(request, f'"{project.title}" was updated.')
            return redirect('portfolio:project_detail', pk=project.pk)
    else:
        form = ProjectForm(instance=project)
    return render(request, 'portfolio/project_form.html', {
        'form': form, 'mode': 'edit', 'project': project,
    })


@owner_required
@require_POST
def delete_project(request, pk):
    project = get_object_or_404(Project, pk=pk)
    title = project.title
    project.delete()
    messages.success(request, f'"{title}" was removed.')
    return redirect('portfolio:manage_projects')


@owner_required
def manage_projects(request):
    return render(request, 'portfolio/project_manage.html', {'projects': Project.objects.all()})


@owner_required
def manage_profile(request):
    profile = SiteProfile.load()
    if request.method == 'POST':
        form = SiteProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated.')
            return redirect('portfolio:manage_profile')
    else:
        form = SiteProfileForm(instance=profile)
    return render(request, 'portfolio/manage_profile_form.html', {'form': form})


SIMPLE_CONTENT = {
    'stats': {
        'model': Stat, 'form': StatForm, 'label': 'Stats', 'singular': 'Stat',
        'help_text': 'Small headline numbers shown in the hero, e.g. "3+ Years Editing".',
    },
    'tools': {
        'model': Tool, 'form': ToolForm, 'label': 'Tools', 'singular': 'Tool',
        'help_text': 'Software badges shown in the Tools & Skills section.',
    },
    'experience': {
        'model': ExperienceEntry, 'form': ExperienceForm, 'label': 'Experience', 'singular': 'Experience entry',
        'help_text': 'Rows shown in the Experience timeline.',
    },
}


def _content_config(key):
    config = SIMPLE_CONTENT.get(key)
    if not config:
        raise Http404(f'Unknown content type "{key}".')
    return config


@owner_required
def manage_content_list(request, key):
    config = _content_config(key)
    items = config['model'].objects.all()
    return render(request, 'portfolio/manage_content_list.html', {
        'items': items, 'key': key, 'label': config['label'], 'singular': config['singular'],
        'help_text': config['help_text'],
    })


@owner_required
def manage_content_edit(request, key, pk=None):
    config = _content_config(key)
    instance = get_object_or_404(config['model'], pk=pk) if pk else None
    if request.method == 'POST':
        form = config['form'](request.POST, instance=instance)
        if form.is_valid():
            form.save()
            messages.success(request, 'Saved.')
            return redirect('portfolio:manage_content_list', key=key)
    else:
        form = config['form'](instance=instance)
    return render(request, 'portfolio/manage_content_form.html', {
        'form': form, 'key': key, 'label': config['label'], 'singular': config['singular'],
        'mode': 'edit' if pk else 'add',
    })


@owner_required
@require_POST
def manage_content_delete(request, key, pk):
    config = _content_config(key)
    instance = get_object_or_404(config['model'], pk=pk)
    instance.delete()
    messages.success(request, 'Removed.')
    return redirect('portfolio:manage_content_list', key=key)


@owner_required
def manage_skills(request):
    groups = SkillGroup.objects.prefetch_related('items').all()
    return render(request, 'portfolio/manage_skills_list.html', {'groups': groups})


@owner_required
def manage_skill_add(request):
    if request.method == 'POST':
        form = SkillGroupForm(request.POST)
        if form.is_valid():
            group = form.save()
            messages.success(request, f'"{group.name}" created — now add its skill items below.')
            return redirect('portfolio:manage_skill_edit', pk=group.pk)
    else:
        form = SkillGroupForm()
    return render(request, 'portfolio/manage_skill_form.html', {'form': form, 'formset': None, 'mode': 'add'})


@owner_required
def manage_skill_edit(request, pk):
    group = get_object_or_404(SkillGroup, pk=pk)
    if request.method == 'POST':
        form = SkillGroupForm(request.POST, instance=group)
        formset = SkillItemFormSet(request.POST, instance=group)
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            messages.success(request, 'Skill group updated.')
            return redirect('portfolio:manage_skills')
    else:
        form = SkillGroupForm(instance=group)
        formset = SkillItemFormSet(instance=group)
    return render(request, 'portfolio/manage_skill_form.html', {
        'form': form, 'formset': formset, 'mode': 'edit', 'group': group,
    })


@owner_required
@require_POST
def manage_skill_delete(request, pk):
    group = get_object_or_404(SkillGroup, pk=pk)
    group.delete()
    messages.success(request, 'Skill group removed.')
    return redirect('portfolio:manage_skills')


def portfolio_login(request):
    if request.user.is_authenticated:
        return redirect('portfolio:home')

    form = AuthenticationForm(request, data=(request.POST or None))
    for field in form.fields.values():
        field.widget.attrs['class'] = 'form-input'

    if request.method == 'POST':
        if form.is_valid():
            auth_login(request, form.get_user())
            next_url = request.POST.get('next') or request.GET.get('next')
            return redirect(next_url or 'portfolio:home')
        messages.error(request, 'Invalid username or password.')

    return render(request, 'portfolio/login.html', {'form': form})
