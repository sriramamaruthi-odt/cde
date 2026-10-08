from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import OrganizationTool, Tool, UserTool


class ToolSerializer(serializers.ModelSerializer):
    label = serializers.CharField(source="get_name_display", read_only=True)

    class Meta:
        model = Tool
        fields = ["id", "name", "label", "description"]


def _full_clean_and_save(instance):
    try:
        instance.full_clean()
    except DjangoValidationError as exc:
        raise serializers.ValidationError(exc.message_dict)
    instance.save()
    return instance


class OrganizationToolSerializer(serializers.ModelSerializer):
    tool_detail = ToolSerializer(source="tool", read_only=True)

    class Meta:
        model = OrganizationTool
        fields = ["id", "organization", "tool", "tool_detail", "assigned_by", "assigned_at"]
        read_only_fields = ["organization", "assigned_by", "assigned_at"]

    def create(self, validated_data):
        return _full_clean_and_save(OrganizationTool(**validated_data))


class UserToolSerializer(serializers.ModelSerializer):
    tool_detail = ToolSerializer(source="tool", read_only=True)

    class Meta:
        model = UserTool
        fields = ["id", "user", "tool", "tool_detail", "assigned_by", "assigned_at"]
        read_only_fields = ["user", "assigned_by", "assigned_at"]

    def create(self, validated_data):
        return _full_clean_and_save(UserTool(**validated_data))


class ToolIdsSerializer(serializers.Serializer):
    """Request body for POST/PUT/PATCH/DELETE on UserToolView: {"tools": [<id>, ...]}."""

    tools = serializers.PrimaryKeyRelatedField(queryset=Tool.objects.all(), many=True)
