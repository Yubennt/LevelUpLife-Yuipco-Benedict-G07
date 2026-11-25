from django.db import migrations

LEVELS_TO_SEED = 100
TITLES = ["Novice", "Apprentice", "Adventurer", "Challenger", "Veteran",
          "Expert", "Master", "Champion", "Legend", "Mythic"]


def seed_levels(apps, schema_editor):
    Level = apps.get_model("gamification", "Level")
    Level.objects.bulk_create(
        Level(level_number=n, xp_required=50 * n * (n - 1), title=TITLES[min(n, len(TITLES)) - 1])
        for n in range(1, LEVELS_TO_SEED + 1)
    )


def unseed_levels(apps, schema_editor):
    apps.get_model("gamification", "Level").objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [("gamification", "0001_initial")]
    operations = [migrations.RunPython(seed_levels, unseed_levels)]
