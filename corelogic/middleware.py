from django.conf import settings
from django.http import HttpResponsePermanentRedirect


class CanonicalHostRedirectMiddleware:
    """Redirect platform hostnames to the configured public domain."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        canonical_host = getattr(settings, 'DOMAIN', '')
        if not canonical_host:
            return self.get_response(request)

        current_host = request.get_host().split(':')[0].lower()
        canonical_host = canonical_host.lower()
        custom_hosts = {host.lower() for host in getattr(settings, 'CUSTOM_DOMAIN_HOSTS', [])}
        platform_hosts = tuple(
            host.lower()
            for host in getattr(settings, 'PLATFORM_HOSTS', [])
            if host.startswith('.')
        )

        should_redirect = (
            current_host not in custom_hosts
            and any(current_host.endswith(platform_host) for platform_host in platform_hosts)
        )
        if should_redirect:
            target_url = request.build_absolute_uri().replace(
                request.get_host(),
                canonical_host,
                1,
            )
            return HttpResponsePermanentRedirect(target_url)

        return self.get_response(request)
