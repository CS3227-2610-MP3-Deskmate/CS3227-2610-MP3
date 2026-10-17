"""Middleware that tells browsers and proxies not to store Deskmate's responses."""

from django.utils.cache import patch_cache_control


def no_store(get_response):
    """Add `no-store` to every response's `Cache-Control` header (ACC-1.8)."""

    def middleware(request):
        response = get_response(request)
        patch_cache_control(response, no_store=True)
        return response

    return middleware
