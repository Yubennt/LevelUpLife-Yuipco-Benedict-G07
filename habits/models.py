import datetime
from django.db import models
from django.conf import settings
from django.utils import timezone


class Tag(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='tags')
    name = models.CharField(max_length=30)

    class Meta:
        db_table = 'tags'
        constraints = [
            models.UniqueConstraint(fields=['user', 'name'], name='unique_user_tag_name')
        ]

    def __str__(self):
        return self.name


class HabitQuerySet(models.QuerySet):
    def active(self):
        return self.filter(deleted_at__isnull=True)


class HabitManager(models.Manager):
    def get_queryset(self):
        return HabitQuerySet(self.model, using=self._db).active()

    def with_deleted(self):
        return HabitQuerySet(self.model, using=self._db)


class Habit(models.Model):
    FREQUENCY_CHOICES = [
        ('DAILY', 'Daily'),
        ('WEEKLY', 'Weekly'),
    ]
    DIFFICULTY_CHOICES = [
        ('EASY', 'Easy (10 XP)'),
        ('MEDIUM', 'Medium (20 XP)'),
        ('HARD', 'Hard (30 XP)'),
    ]
    XP_MAP = {'EASY': 10, 'MEDIUM': 20, 'HARD': 30}

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='habits')
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    frequency = models.CharField(max_length=10, choices=FREQUENCY_CHOICES, default='DAILY')
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, default='EASY')
    xp_reward = models.PositiveSmallIntegerField(default=10)
    start_date = models.DateField(default=datetime.date.today)
    reminder_time = models.TimeField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(blank=True, null=True)

    tags = models.ManyToManyField(Tag, through='HabitTag', related_name='habits', blank=True)

    objects = HabitManager()

    class Meta:
        db_table = 'habits'

    def save(self, *args, **kwargs):
        self.xp_reward = self.XP_MAP.get(self.difficulty, 10)
        super().save(*args, **kwargs)

    def soft_delete(self):
        self.deleted_at = timezone.now()
        self.is_active = False
        self.save()

    def __str__(self):
        return f"{self.title} ({self.user.email})"


class HabitTag(models.Model):
    habit = models.ForeignKey(Habit, on_delete=models.CASCADE)
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE)

    class Meta:
        db_table = 'habit_tags'
        unique_together = ('habit', 'tag')


class HabitStreak(models.Model):
    habit = models.ForeignKey(Habit, on_delete=models.CASCADE, related_name='streaks')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    current_streak = models.PositiveIntegerField(default=0)
    longest_streak = models.PositiveIntegerField(default=0)
    last_completed_date = models.DateField(null=True, blank=True)

    class Meta:
        db_table = 'habit_streaks'

    def __str__(self):
        return f"{self.habit.title} Streak: {self.current_streak}"


class HabitLog(models.Model):
    habit = models.ForeignKey(Habit, on_delete=models.CASCADE, related_name='logs')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    completed_at = models.DateTimeField(default=timezone.now)
    completed_date = models.DateField(default=timezone.now)
    xp_earned = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'habit_logs'
        unique_together = ('habit', 'completed_date')
        ordering = ['-completed_at']

    def __str__(self):
        return f"{self.user.username} - {self.habit.title} ({self.completed_date})"