from django.contrib import admin

from .models import BeneficiaryGroup, Organization, OrganizationTool, Sector, Tool, UserTool


@admin.register(Sector)
class SectorAdmin(admin.ModelAdmin):
    search_fields = ("name",)


@admin.register(BeneficiaryGroup)
class BeneficiaryGroupAdmin(admin.ModelAdmin):
    search_fields = ("name",)


@admin.register(Tool)
class ToolAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


class OrganizationToolInline(admin.TabularInline):
    model = OrganizationTool
    extra = 1
    autocomplete_fields = ("assigned_by",)


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "year_established", "annual_operating_budget", "total_team_size")
    search_fields = ("name",)
    filter_horizontal = ("states_of_operation", "sectors", "beneficiary_groups")
    inlines = [OrganizationToolInline]


@admin.register(UserTool)
class UserToolAdmin(admin.ModelAdmin):
    list_display = ("user", "tool", "assigned_by", "assigned_at")
    list_filter = ("tool", "user__role")
    search_fields = ("user__name", "assigned_by__name")
    autocomplete_fields = ("user", "assigned_by")
