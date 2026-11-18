from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import F, OuterRef, Subquery
from django.shortcuts import redirect, render
from django.utils import timezone

from accounts.decorators import admin_required, member_required
from gamification.models import Level
from gamification.services import level_progress

User = get_user_model()


def home(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    return render(request, "landing.html")


@login_required
def dashboard_router(request):
    """After login, each user goes to the dashboard for their role (staff = admin)."""
    return redirect("admin_dashboard" if request.user.is_staff else "user_dashboard")


@member_required
def user_dashboard(request):
    return render(request, "dashboard/user.html", {"progress": level_progress(request.user)})


@admin_required
def admin_dashboard(request):
    """Baseline health indicators and a quick integrity check (F-12), plus account overview (F-11)."""
    week_ago = timezone.now() - timedelta(days=7)
    expected_level = Level.objects.filter(xp_required__lte=OuterRef("total_xp")).order_by("-level_number").values("level_number")[:1]
    mismatched = User.objects.annotate(expected=Subquery(expected_level)).exclude(current_level=F("expected"))
    users = User.objects.all()
    context = {
        "total_users": users.count(),
        "active_users": users.filter(is_active=True).count(),
        "inactive_users": users.filter(is_active=False).count(),
        "staff_users": users.filter(is_staff=True).count(),
        "new_this_week": users.filter(date_joined__gte=week_ago).count(),
        "level_count": Level.objects.count(),
        "level_mismatches": mismatched.count(),
        "recent_users": users.select_related("current_level").order_by("-date_joined")[:25],
    }
    return render(request, "dashboard/admin.html", context)
