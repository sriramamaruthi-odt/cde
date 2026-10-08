from django.db import migrations

LANGUAGES = [
    "Hindi", "Bengali", "Marathi", "Telugu", "Tamil", "Gujarati", "Urdu",
    "Kannada", "Odia", "Malayalam", "Punjabi", "Assamese", "Maithili",
    "Santali", "Kashmiri", "Konkani", "Sindhi", "Dogri", "Meitei (Manipuri)",
    "Bodo", "Sanskrit", "Nepali",
]


def seed_languages(apps, schema_editor):
    Language = apps.get_model("users", "Language")
    Language.objects.bulk_create(
        [Language(name=name) for name in LANGUAGES],
        ignore_conflicts=True,
    )


def unseed_languages(apps, schema_editor):
    Language = apps.get_model("users", "Language")
    Language.objects.filter(name__in=LANGUAGES).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_languages, unseed_languages),
    ]
