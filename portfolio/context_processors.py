from .models import SiteProfile


def site_profile(request):
    """Makes `profile` available in every template without each view passing it."""
    return {'profile': SiteProfile.load()}
