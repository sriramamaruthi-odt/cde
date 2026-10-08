from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver

from users.models import State, UserProfile


class Tool(models.Model):
    """A GV tool (moderation-interface, case-manager, dist-mod, ...).

    A platform admin grants tools to an Organization (OrganizationTool).
    An org-admin's authority to hand tools to coordinators comes from that
    grant directly, so it survives an org-admin being replaced. A
    coordinator, and in turn a cde, get their own personal grant (UserTool),
    each checked against the level above.
    """

    class Key(models.TextChoices):
        MODERATION_INTERFACE = "moderation-interface", "Moderation Interface"
        CASE_MANAGER = "case-manager", "Case Manager"
        DIST_MOD = "dist-mod", "Dist Mod"

    name = models.CharField(max_length=100, choices=Key.choices, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.get_name_display()


class Sector(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name


class BeneficiaryGroup(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name


class Organization(models.Model):
    class Budget(models.TextChoices):
        UNDER_50L = "< ₹50 lakh", "< ₹50 lakh"
        L50_TO_2CR = "₹50 lakh - ₹2 crore", "₹50 lakh - ₹2 crore"
        CR2_TO_5CR = "₹2 crore - ₹5 crore", "₹2 crore - ₹5 crore"
        OVER_5CR = "> ₹5 crore", "> ₹5 crore"

    # --- Sheet 3 fields ---
    name = models.CharField(max_length=255)
    year_established = models.PositiveSmallIntegerField(null=True, blank=True)
    address = models.TextField(blank=True)
    states_of_operation = models.ManyToManyField(
        State, related_name="organizations", blank=True
    )
    sectors = models.ManyToManyField(Sector, related_name="organizations", blank=True)
    sector_other_detail = models.CharField(max_length=255, blank=True)
    beneficiary_groups = models.ManyToManyField(
        BeneficiaryGroup, related_name="organizations", blank=True
    )
    beneficiary_group_other_detail = models.CharField(max_length=255, blank=True)
    tools = models.ManyToManyField(
        Tool, through="OrganizationTool", related_name="organizations", blank=True
    )
    annual_beneficiaries_reached = models.PositiveIntegerField(null=True, blank=True)
    annual_operating_budget = models.CharField(
        max_length=30, choices=Budget.choices, blank=True
    )
    total_team_size = models.PositiveIntegerField(null=True, blank=True)
    field_staff_count = models.PositiveIntegerField(null=True, blank=True)
    description = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class OrganizationTool(models.Model):
    """A tool a platform admin has granted to an organization.

    Org-admins may hand out any tool the organization holds here - their
    ability to do so is not itself a row in any table, so replacing the
    org-admin never requires re-granting the organization's tools.
    """

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="tool_grants"
    )
    tool = models.ForeignKey(Tool, on_delete=models.CASCADE, related_name="organization_grants")
    assigned_by = models.ForeignKey(
        UserProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="organization_tools_granted",
        limit_choices_to={"role": UserProfile.Role.ADMIN},
    )
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("organization", "tool")]

    def __str__(self):
        return f"{self.organization} - {self.tool}"


class UserTool(models.Model):
    """A tool granted to a specific coordinator or cde.

    A coordinator's grant must come from an org-admin of the same
    organization and be one of that organization's OrganizationTool
    grants. A cde's grant must come from a coordinator of the same
    organization and be one of that coordinator's own UserTool grants.
    """

    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="tool_grants")
    tool = models.ForeignKey(Tool, on_delete=models.CASCADE, related_name="user_grants")
    assigned_by = models.ForeignKey(
        UserProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="user_tools_granted",
    )
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("user", "tool")]

    def __str__(self):
        return f"{self.user} - {self.tool}"

    def clean(self):
        super().clean()
        if self.user.role not in (UserProfile.Role.COORDINATOR, UserProfile.Role.CDE):
            raise ValidationError({"user": "Only coordinators and cde can hold a tool grant."})

        if self.user.role == UserProfile.Role.COORDINATOR:
            if not self.assigned_by or self.assigned_by.role != UserProfile.Role.ORG_ADMIN:
                raise ValidationError(
                    {"assigned_by": "A coordinator's tool must be granted by an org-admin."}
                )
            if self.assigned_by.organization_id != self.user.organization_id:
                raise ValidationError(
                    {"assigned_by": "The org-admin must belong to the coordinator's organization."}
                )
            if not OrganizationTool.objects.filter(
                organization_id=self.user.organization_id, tool=self.tool
            ).exists():
                raise ValidationError(
                    {"tool": "This organization has not been granted this tool."}
                )

        elif self.user.role == UserProfile.Role.CDE:
            if not self.assigned_by or self.assigned_by.role != UserProfile.Role.COORDINATOR:
                raise ValidationError(
                    {"assigned_by": "A cde's tool must be granted by a coordinator."}
                )
            if self.assigned_by.organization_id != self.user.organization_id:
                raise ValidationError(
                    {"assigned_by": "The coordinator must belong to the cde's organization."}
                )
            if not UserTool.objects.filter(user=self.assigned_by, tool=self.tool).exists():
                raise ValidationError(
                    {"tool": "This coordinator has not been granted this tool."}
                )


@receiver(post_delete, sender=OrganizationTool)
def _revoke_coordinator_grants_on_org_tool_removed(sender, instance, **kwargs):
    """Losing a tool at the org level revokes it from every coordinator in that org."""
    UserTool.objects.filter(
        user__organization_id=instance.organization_id,
        user__role=UserProfile.Role.COORDINATOR,
        tool_id=instance.tool_id,
    ).delete()


@receiver(post_delete, sender=UserTool)
def _revoke_cde_grants_on_coordinator_tool_removed(sender, instance, **kwargs):
    """Losing a tool at the coordinator level revokes it from every cde they granted it to."""
    if instance.user_id is None:
        return
    UserTool.objects.filter(assigned_by_id=instance.user_id, tool_id=instance.tool_id).delete()
