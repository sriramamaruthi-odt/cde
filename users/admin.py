from django.contrib import admin

from organizations.models import UserTool

from .models import (
    Badge,
    Block,
    District,
    Language,
    Location,
    PhoneOTP,
    Skill,
    State,
    UserProfile,
)


@admin.register(State)
class StateAdmin(admin.ModelAdmin):
    search_fields = ("name",)


@admin.register(District)
class DistrictAdmin(admin.ModelAdmin):
    list_display = ("name", "state")
    list_filter = ("state",)
    search_fields = ("name",)


@admin.register(Block)
class BlockAdmin(admin.ModelAdmin):
    list_display = ("name", "district")
    list_filter = ("district__state",)
    search_fields = ("name",)


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ("pincode", "block")
    search_fields = ("pincode", "block__name", "block__district__name", "block__district__state__name")


@admin.register(Language)
class LanguageAdmin(admin.ModelAdmin):
    search_fields = ("name",)


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    search_fields = ("name",)


@admin.register(Badge)
class BadgeAdmin(admin.ModelAdmin):
    list_display = ("title",)


class UserToolInline(admin.TabularInline):
    model = UserTool
    fk_name = "user"
    extra = 1
    autocomplete_fields = ("assigned_by",)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "role",
        "phone_number",
        "is_phone_verified",
        "gender",
        "age",
        "organization",
        "badge",
        "location",
    )
    list_filter = ("role", "gender", "education", "badge", "organization", "is_phone_verified")
    search_fields = ("name", "phone_number")
    filter_horizontal = ("languages", "skills")
    inlines = [UserToolInline]


@admin.register(PhoneOTP)
class PhoneOTPAdmin(admin.ModelAdmin):
    list_display = ("phone_number", "code", "is_verified", "attempts", "created_at", "expires_at")
    list_filter = ("is_verified",)
    search_fields = ("phone_number",)
    readonly_fields = ("created_at",)
