from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserCreationForm

from .models import User


class AdminAddUserForm(UserCreationForm):
    class Meta:
        model = User
        fields = ("email", "display_name")


@admin.register(User)
class UserAdmin(UserAdmin):
    """F-11: admins view registrations and deactivate/reactivate accounts. Every action is written to
    the Django admin log (BR-31). Only is_staff accounts can open this site (BR-04)."""

    add_form = AdminAddUserForm
    ordering = ("email",)
    list_display = ("email", "display_name", "current_level", "total_xp", "is_active", "is_staff", "date_joined")
    list_filter = ("is_active", "is_staff", "is_superuser")
    search_fields = ("email", "display_name")
    readonly_fields = ("total_xp", "current_level", "last_login", "date_joined")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Profile", {"fields": ("display_name", "personal_goal", "time_zone", "reminders_enabled")}),
        ("Progress (managed by the gamification service)", {"fields": ("total_xp", "current_level")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("email", "display_name", "password1", "password2")}),
    )
    actions = ["deactivate_accounts", "reactivate_accounts"]

    def _set_active(self, request, queryset, active):
        changed = 0
        for user in queryset.exclude(pk=request.user.pk).filter(is_active=not active):
            user.is_active = active
            user.save(update_fields=["is_active"])
            self.log_change(request, user, "Reactivated account" if active else "Deactivated account")
            changed += 1
        self.message_user(request, f"{changed} account(s) {'reactivated' if active else 'deactivated'}. "
                                   "Your own account is never changed by this action.", messages.SUCCESS)

    @admin.action(description="Deactivate selected accounts")
    def deactivate_accounts(self, request, queryset):
        self._set_active(request, queryset, False)

    @admin.action(description="Reactivate selected accounts")
    def reactivate_accounts(self, request, queryset):
        self._set_active(request, queryset, True)
