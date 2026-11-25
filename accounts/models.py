from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.functions import Lower

from gamification.models import Level

from .validators import validate_time_zone


class UserManager(BaseUserManager):
    use_in_migrations = True

    def get_by_natural_key(self, email):
        """Case-insensitive lookup so 'Ana@x.com' and 'ana@x.com' are the same login (BR-01)."""
        return self.get(email__iexact=email.strip())

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("An email address is required.")
        user = self.model(email=email.strip().lower(), **extra_fields)
        user.password = make_password(password)  # salted hash (BR-02)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields["is_staff"] = True
        extra_fields["is_superuser"] = True
        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    """SDD 4.3 `users` table. Email is the login field; username/first/last name are removed."""

    username = None
    first_name = None
    last_name = None

    email = models.EmailField("email address", max_length=254, unique=True)
    display_name = models.CharField(max_length=50)
    personal_goal = models.TextField(blank=True, null=True)
    time_zone = models.CharField(max_length=50, default="UTC", validators=[validate_time_zone])
    reminders_enabled = models.BooleanField(default=True)
    total_xp = models.IntegerField(default=0)
    current_level = models.ForeignKey(
        Level, to_field="level_number", db_column="current_level", default=1,
        on_delete=models.PROTECT, related_name="users",
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["display_name"]

    objects = UserManager()

    class Meta:
        db_table = "users"
        verbose_name = "user"
        constraints = [
            # BR-01: case-insensitive unique email
            models.UniqueConstraint(Lower("email"), name="users_email_ci_unique"),
            # BR-18: total XP never negative
            models.CheckConstraint(condition=models.Q(total_xp__gte=0), name="users_total_xp_gte_0"),
        ]

    def __str__(self):
        return self.email

    def save(self, *args, **kwargs):
        self.email = (self.email or "").strip().lower()
        update_fields = kwargs.get("update_fields")
        # BR-19/BR-20: the level is recalculated whenever XP is saved.
        if update_fields is None or "total_xp" in update_fields:
            level = Level.for_xp(self.total_xp)
            if level is not None:
                self.current_level_id = level.level_number
                if update_fields is not None:
                    kwargs["update_fields"] = {*update_fields, "current_level"}
        super().save(*args, **kwargs)

    def get_full_name(self):
        return self.display_name

    def get_short_name(self):
        return self.display_name

    @property
    def is_admin_role(self):
        """BR-04: administrators are the accounts flagged is_staff."""
        return self.is_staff
