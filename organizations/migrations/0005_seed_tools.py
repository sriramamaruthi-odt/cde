from django.db import migrations

TOOLS = [
    "moderation-interface",
    "case-manager",
    "dist-mod",
]


def seed_tools(apps, schema_editor):
    Tool = apps.get_model("organizations", "Tool")
    Tool.objects.bulk_create([Tool(name=name) for name in TOOLS], ignore_conflicts=True)


def unseed_tools(apps, schema_editor):
    Tool = apps.get_model("organizations", "Tool")
    Tool.objects.filter(name__in=TOOLS).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("organizations", "0004_tool_organizationtool_organization_tools_usertool"),
    ]

    operations = [
        migrations.RunPython(seed_tools, unseed_tools),
    ]
