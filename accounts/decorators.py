from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect


def access_required(*, staff):
    """Restrict a view to administrators (staff=True) or regular users (staff=False).

    Logged-out users go to the login page; the other kind of user is sent back to their own dashboard.
    """

    def decorator(view):
        @wraps(view)
        @login_required
        def wrapper(request, *args, **kwargs):
            if request.user.is_staff != staff:
                messages.error(request, "You don't have access to that page.")
                return redirect("dashboard")
            return view(request, *args, **kwargs)

        return wrapper

    return decorator


admin_required = access_required(staff=True)
member_required = access_required(staff=False)
