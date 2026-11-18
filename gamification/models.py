from django.db import models


class Level(models.Model):
    """Level thresholds (SDD 4.3). BR-19: xp_required = 50 * n * (n - 1). Seeded by a data migration."""

    level_number = models.IntegerField(primary_key=True)
    xp_required = models.IntegerField(unique=True)
    title = models.CharField(max_length=50)

    class Meta:
        db_table = "levels"
        ordering = ["level_number"]
        constraints = [
            models.CheckConstraint(condition=models.Q(level_number__gte=1), name="levels_level_number_gte_1"),
            models.CheckConstraint(condition=models.Q(xp_required__gte=0), name="levels_xp_required_gte_0"),
        ]

    def __str__(self):
        return f"Level {self.level_number}: {self.title}"

    @classmethod
    def for_xp(cls, total_xp):
        """BR-19: the highest level whose required XP is <= total XP."""
        return cls.objects.filter(xp_required__lte=total_xp).order_by("-level_number").first()
