from datetime import timedelta
from django.utils import timezone
from .models import HabitLog

def calculate_habit_streak(habit):
    """Calculates consecutive days completed up to today or yesterday."""
    logs = HabitLog.objects.filter(habit=habit).order_by('-completed_date').values_list('completed_date', flat=True)
    if not logs:
        return 0

    log_dates = set(logs)
    today = timezone.now().date()
    yesterday = today - timedelta(days=1)

    # Streak is active if logged today or yesterday
    if today in log_dates:
        current_check = today
    elif yesterday in log_dates:
        current_check = yesterday
    else:
        return 0

    streak = 0
    while current_check in log_dates:
        streak += 1
        current_check -= timedelta(days=1)

    return streak