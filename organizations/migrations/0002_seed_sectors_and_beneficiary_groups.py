from django.db import migrations

SECTORS = [
    "Agriculture",
    "Education",
    "Health",
    "Rural Development",
    "Urban Development",
    "Digital Services",
    "Communication",
    "Banking, Finance & Insurance",
    "Culture",
    "Enterprise development",
    "Others (please specify)",
]

BENEFICIARY_GROUPS = [
    "Farmers",
    "Youth",
    "Women & Self-Help Groups (SHGs)",
    "Ultra poors",
    "Rural Entrepreneurs",
    "Vulnerable groups",
    "Persons with Disabilities (PwD)",
    "General Public",
    "Others (please specify)",
]


def seed(apps, schema_editor):
    Sector = apps.get_model("organizations", "Sector")
    BeneficiaryGroup = apps.get_model("organizations", "BeneficiaryGroup")
    Sector.objects.bulk_create(
        [Sector(name=name) for name in SECTORS], ignore_conflicts=True
    )
    BeneficiaryGroup.objects.bulk_create(
        [BeneficiaryGroup(name=name) for name in BENEFICIARY_GROUPS], ignore_conflicts=True
    )


def unseed(apps, schema_editor):
    Sector = apps.get_model("organizations", "Sector")
    BeneficiaryGroup = apps.get_model("organizations", "BeneficiaryGroup")
    Sector.objects.filter(name__in=SECTORS).delete()
    BeneficiaryGroup.objects.filter(name__in=BENEFICIARY_GROUPS).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("organizations", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
