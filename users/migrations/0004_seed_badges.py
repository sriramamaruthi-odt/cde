from django.db import migrations

BADGES = [
    ("lead", "Mentor"),
    ("advanced", "Expert"),
    ("active", "Practitioner"),
    ("emerging", "Learner"),
]


def seed_badges(apps, schema_editor):
    Badge = apps.get_model("users", "Badge")
    Badge.objects.bulk_create(
        [Badge(level=level, title=title) for level, title in BADGES],
        ignore_conflicts=True,
    )


def unseed_badges(apps, schema_editor):
    Badge = apps.get_model("users", "Badge")
    Badge.objects.filter(level__in=[level for level, _ in BADGES]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0003_badge_alter_userprofile_badge"),
    ]

    operations = [
        migrations.RunPython(seed_badges, unseed_badges),
    ]
