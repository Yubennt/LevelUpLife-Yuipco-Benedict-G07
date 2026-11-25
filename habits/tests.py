from datetime import timedelta
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from habits.models import Habit, HabitLog
from habits.services import calculate_habit_streak
from gamification.models import Level

User = get_user_model()

class GamificationHabitTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="testplayer@example.com", 
            password="password123"
        )
        self.level1, _ = Level.objects.get_or_create(
            level_number=1, 
            defaults={"title": "Novice", "xp_required": 0}
        )
        self.level2, _ = Level.objects.get_or_create(
            level_number=2, 
            defaults={"title": "Apprentice", "xp_required": 10}
        )
        self.user.current_level = self.level1
        self.user.save()

        self.habit = Habit.objects.create(
            user=self.user,
            title="Morning Swim",
            frequency="daily",
            xp_reward=10,
            is_active=True
        )
        # Bypasses django-axes authentication middleware check
        self.client.force_login(self.user)
        self.toggle_url = reverse('habits:habit_toggle', kwargs={'pk': self.habit.pk})

    def test_toggle_habit_creates_log_and_awards_xp(self):
        response = self.client.post(self.toggle_url)
        self.assertEqual(response.status_code, 302)

        self.user.refresh_from_db()
        self.assertEqual(self.user.total_xp, 10)
        self.assertTrue(HabitLog.objects.filter(habit=self.habit, user=self.user).exists())

    def test_level_up_on_habit_completion(self):
        self.client.post(self.toggle_url)
        self.user.refresh_from_db()
        self.assertEqual(self.user.current_level, self.level2)

    def test_unchecking_habit_removes_log_and_xp(self):
        self.client.post(self.toggle_url)
        self.client.post(self.toggle_url)

        self.user.refresh_from_db()
        self.assertEqual(self.user.total_xp, 0)
        self.assertFalse(HabitLog.objects.filter(habit=self.habit, user=self.user).exists())

    def test_streak_calculation(self):
        today = timezone.now().date()
        HabitLog.objects.create(habit=self.habit, user=self.user, completed_date=today - timedelta(days=1), xp_earned=10)
        HabitLog.objects.create(habit=self.habit, user=self.user, completed_date=today, xp_earned=10)

        streak = calculate_habit_streak(self.habit)
        self.assertEqual(streak, 2)
        