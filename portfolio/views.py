from functools import wraps

from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from .editing import EDIT_REGIONS, build_form, build_formset, get_region
from .forms import ProjectForm, SiteProfileForm, SkillGroupForm, SkillItemFormSet
from .models import ExperienceEntry, Project, SiteProfile, SkillGroup, Stat, Tool


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
        'projects': Project.objects.prefetch_related('videos'),
    }
    return render(request, 'portfolio/home.html', context)


def project_detail(request, pk):
    project = get_object_or_404(Project.objects.prefetch_related('videos', 'gallery'), pk=pk)
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


# Derived from the edit-region registry so stats/tools/experience are defined exactly once.
SIMPLE_CONTENT = {
    key: {
        'model': region.model,
        'form': region.form_class,
        'label': region.list_label,
        'singular': region.singular,
        'help_text': region.blurb,
    }
    for key, region in EDIT_REGIONS.items() if region.simple_content
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
        form = config['form'](request.POST, request.FILES, instance=instance)
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


PANEL_FRAGMENT_TEMPLATE = 'portfolio/manage/_panel.html'
PANEL_PAGE_TEMPLATE = 'portfolio/manage/panel_page.html'


def _panel_template(request):
    """Same context either way: the fragment for the drawer, a full page otherwise."""
    return PANEL_FRAGMENT_TEMPLATE if request.headers.get('X-Panel') == '1' else PANEL_PAGE_TEMPLATE


def _panel_next_url(request, region, instance=None):
    """Where Save/Cancel lands. Only same-origin targets are honoured."""
    candidate = request.POST.get('next') or request.GET.get('next')
    if candidate and url_has_allowed_host_and_scheme(
        candidate, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return candidate
    if region.kind == 'instance' and hasattr(instance, 'get_absolute_url'):
        return instance.get_absolute_url()
    return f"{reverse('portfolio:home')}#{region.anchor}"


def _full_editor_url(region, instance):
    if not region.fallback_url:
        return ''
    args = [instance.pk] if region.fallback_takes_pk and instance is not None else region.fallback_args
    return reverse(region.fallback_url, args=args)


def _panel_mode(request, region, pk):
    if region.kind == 'profile' or pk is not None:
        return 'edit'
    if request.resolver_match and request.resolver_match.url_name == 'edit_panel_new':
        return 'add'
    return 'index'


@owner_required
@never_cache
def edit_panel(request, key, pk=None):
    region = get_region(key)
    if region.kind == 'instance' and pk is None:
        raise Http404('This region always edits one specific item.')
    if pk is not None and region.model is None:
        raise Http404('This region is not a list of items.')
    mode = _panel_mode(request, region, pk)

    # Model comes from the registry and pk from the <int:pk> converter, so an
    # attacker can neither pick the table nor reach outside it.
    instance = get_object_or_404(region.model, pk=pk) if pk is not None else None
    next_url = _panel_next_url(request, region, instance)
    context = {
        'region': region,
        'mode': mode,
        'next_url': next_url,
        'full_editor_url': _full_editor_url(region, instance),
    }

    if mode == 'index':
        context['items'] = region.model.objects.all()
        return render(request, _panel_template(request), context)

    context['instance'] = instance
    context['can_delete'] = region.kind in ('collection', 'nested') and instance is not None

    if request.method == 'POST':
        form = build_form(region, instance=instance, data=request.POST, files=request.FILES)
        formset = build_formset(
            region, instance=instance, data=request.POST, files=request.FILES,
        ) if instance else None
        if (form is None or form.is_valid()) and (formset is None or formset.is_valid()):
            saved = form.save() if form is not None else instance
            if formset is not None:
                formset.save()
            messages.success(request, f'{region.label} — saved.')
            if region.kind == 'nested' and instance is None:
                return redirect('portfolio:edit_panel_item', key=region.key, pk=saved.pk)
            return redirect(next_url)
    else:
        form = build_form(region, instance=instance)
        formset = build_formset(region, instance=instance) if instance else None

    context['form'] = form
    context['formset'] = formset
    return render(request, _panel_template(request), context)


@owner_required
@require_POST
def edit_panel_delete(request, key, pk):
    region = get_region(key)
    if region.kind not in ('collection', 'nested'):
        raise Http404('This region has nothing to delete.')
    instance = get_object_or_404(region.model, pk=pk)
    instance.delete()
    messages.success(request, 'Removed.')
    return redirect(_panel_next_url(request, region))


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
