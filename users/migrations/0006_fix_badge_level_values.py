from django.db import migrations

OLD_TO_NEW = {
    "lead": "Lead CDE",
    "advanced": "Advanced CDE",
    "active": "Active CDE",
    "emerging": "Emerging CDE",
}


def forwards(apps, schema_editor):
    Badge = apps.get_model("users", "Badge")
    for old, new in OLD_TO_NEW.items():
        Badge.objects.filter(level=old).update(level=new)


def backwards(apps, schema_editor):
    Badge = apps.get_model("users", "Badge")
    for old, new in OLD_TO_NEW.items():
        Badge.objects.filter(level=new).update(level=old)


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0005_alter_badge_level_alter_userprofile_education_and_more"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
