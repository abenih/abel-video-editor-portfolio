"""Small inline-SVG icon library used across the portfolio templates.

Keeping icons as plain data here means the templates stay declarative
(`{% icon 'video' %}`) and every icon shares one consistent, dependency-free
source instead of duplicated inline SVG blocks or an external icon font.
"""
from django import template
from django.utils.safestring import mark_safe

register = template.Library()

_STROKE = 'fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"'

_ICONS = {
    'video': f'<svg viewBox="0 0 24 24" {_STROKE}><rect x="3" y="5" width="18" height="14" rx="3"/>'
             f'<path d="M10 9.3v5.4l4.6-2.7z" fill="currentColor" stroke="none"/></svg>',

    'motion': f'<svg viewBox="0 0 24 24" {_STROKE}><circle cx="12" cy="12" r="8.5"/><circle cx="12" cy="12" r="2.2"/>'
              f'<circle cx="12" cy="5.2" r="1.1"/><circle cx="18.8" cy="12" r="1.1"/>'
              f'<circle cx="12" cy="18.8" r="1.1"/><circle cx="5.2" cy="12" r="1.1"/></svg>',

    'design': f'<svg viewBox="0 0 24 24" {_STROKE}><circle cx="9.5" cy="12" r="6"/><circle cx="14.5" cy="12" r="6"/></svg>',

    'thumbnail': f'<svg viewBox="0 0 24 24" {_STROKE}><rect x="3" y="4.5" width="18" height="15" rx="2"/>'
                 f'<circle cx="8.3" cy="9.5" r="1.5"/><path d="M4 16.5l4.8-4.8 3.4 3.4 2.4-2.4L20 17"/></svg>',

    'branding': f'<svg viewBox="0 0 24 24" {_STROKE}><rect x="7" y="7" width="10" height="10" rx="2" '
                f'transform="rotate(45 12 12)"/><circle cx="12" cy="12" r="2"/></svg>',

    'ai': f'<svg viewBox="0 0 24 24" {_STROKE}><path d="M12 3v5M12 16v5M3 12h5M16 12h5"/>'
          f'<circle cx="12" cy="12" r="3.2"/></svg>',

    'all': f'<svg viewBox="0 0 24 24" {_STROKE}><rect x="3.5" y="3.5" width="7" height="7" rx="1.4"/>'
           f'<rect x="13.5" y="3.5" width="7" height="7" rx="1.4"/><rect x="3.5" y="13.5" width="7" height="7" rx="1.4"/>'
           f'<rect x="13.5" y="13.5" width="7" height="7" rx="1.4"/></svg>',

    'clock': f'<svg viewBox="0 0 24 24" {_STROKE}><circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3.2 1.8"/></svg>',

    'check': f'<svg viewBox="0 0 24 24" {_STROKE}><circle cx="12" cy="12" r="8.5"/><path d="m8 12.3 2.6 2.6L16.2 9"/></svg>',

    'folder': f'<svg viewBox="0 0 24 24" {_STROKE}><path d="M4 7a2 2 0 0 1 2-2h3.5l1.8 2H18a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2Z"/></svg>',

    'briefcase': f'<svg viewBox="0 0 24 24" {_STROKE}><rect x="3.5" y="8" width="17" height="11" rx="2"/>'
                 f'<path d="M8.5 8V6.3A1.8 1.8 0 0 1 10.3 4.5h3.4A1.8 1.8 0 0 1 15.5 6.3V8"/><path d="M3.5 13h17"/></svg>',

    'bullet': f'<svg viewBox="0 0 24 24" {_STROKE}><path d="m5 12.5 4.5 4.5L19 7"/></svg>',

    'instagram': f'<svg viewBox="0 0 24 24" {_STROKE}><rect x="3" y="3" width="18" height="18" rx="6"/>'
                 f'<circle cx="12" cy="12" r="4.2"/><circle cx="17" cy="7" r="1" fill="currentColor" stroke="none"/></svg>',

    'facebook': f'<svg viewBox="0 0 24 24" {_STROKE}><circle cx="12" cy="12" r="9"/><path d="M9 8h6M9 8v13M9 12.5h4.5"/></svg>',

    'telegram': f'<svg viewBox="0 0 24 24" {_STROKE}><path d="M3 11 21 4 14 20 11 13 3 11Z"/><path d="M11 13 21 4"/></svg>',

    'pin': f'<svg viewBox="0 0 24 24" {_STROKE}><path d="M12 3 17 9 12 21 7 9Z"/><circle cx="12" cy="9" r="2"/></svg>',
}


@register.simple_tag
def icon(name, css_class=''):
    svg = _ICONS.get(name)
    if not svg:
        return ''
    if css_class:
        svg = svg.replace('<svg ', f'<svg class="{css_class}" ', 1)
    return mark_safe(svg)
