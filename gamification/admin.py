from django.contrib import admin

from .models import Level


@admin.register(Level)
class LevelAdmin(admin.ModelAdmin):
    """Level thresholds are data-driven but fixed by BR-19, so they are view-only here."""

    list_display = ("level_number", "title", "xp_required")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
