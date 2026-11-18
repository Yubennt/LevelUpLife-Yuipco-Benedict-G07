import zoneinfo

from django.utils import timezone


class UserTimezoneMiddleware:
    """Show dates in the logged-in user's own time zone (SDD 5.3)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        tz = None
        if user is not None and user.is_authenticated:
            try:
                tz = zoneinfo.ZoneInfo(user.time_zone)
            except (zoneinfo.ZoneInfoNotFoundError, ValueError):
                tz = None
        if tz:
            timezone.activate(tz)
        else:
            timezone.deactivate()
        return self.get_response(request)
