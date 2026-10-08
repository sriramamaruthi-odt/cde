from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from users.models import UserProfile

from .authentication import ActingAsHeaderAuthentication
from .models import Organization, OrganizationTool, Tool, UserTool
from .permissions import IsResolvedCaller
from .serializers import (
    OrganizationToolSerializer,
    ToolIdsSerializer,
    ToolSerializer,
    UserToolSerializer,
)


def _check_can_manage_user_tool(caller, target):
    """Mirrors UserTool.clean()'s role/organization rule, so a mismatched
    request is rejected with a clear 403 before it reaches model
    validation (which still re-checks everything as the final authority).
    """
    if target.role == UserProfile.Role.COORDINATOR:
        if caller.role != UserProfile.Role.ORG_ADMIN or caller.organization_id != target.organization_id:
            raise PermissionDenied(
                "Only an org-admin of this coordinator's organization can do this."
            )
    elif target.role == UserProfile.Role.CDE:
        if caller.role != UserProfile.Role.COORDINATOR or caller.organization_id != target.organization_id:
            raise PermissionDenied("Only a coordinator of this cde's organization can do this.")
    else:
        raise PermissionDenied("Tools can only be assigned to a coordinator or cde.")


class ToolListView(generics.ListAPIView):
    """Read-only catalog of GV tools, used to populate assignment UIs."""

    queryset = Tool.objects.all()
    serializer_class = ToolSerializer


class OrganizationToolListCreateView(generics.ListCreateAPIView):
    """GET/POST /api/organizations/<organization_id>/tools/

    GET lists the tools currently granted to the organization.
    POST grants one more (body: {"tool": <tool_id>}) - caller must be an
    admin (role=ADMIN); the grant is stamped with assigned_by=caller.
    """

    serializer_class = OrganizationToolSerializer
    authentication_classes = [ActingAsHeaderAuthentication]
    permission_classes = [IsResolvedCaller]

    def get_queryset(self):
        return OrganizationTool.objects.filter(organization_id=self.kwargs["organization_id"])

    def perform_create(self, serializer):
        caller = self.request.user
        if caller.role != UserProfile.Role.ADMIN:
            raise PermissionDenied("Only a platform admin can grant a tool to an organization.")
        organization = get_object_or_404(Organization, pk=self.kwargs["organization_id"])
        serializer.save(organization=organization, assigned_by=caller)


class OrganizationToolDetailView(generics.DestroyAPIView):
    """DELETE /api/organizations/<organization_id>/tools/<tool_id>/

    Revokes a tool from the organization. Caller must be an admin
    (role=ADMIN). Revoking here cascades: every coordinator in the
    organization who was granted this tool loses it, and every cde any
    of those coordinators had granted it to loses it in turn (see the
    post_delete signals on OrganizationTool/UserTool in models.py).
    """

    serializer_class = OrganizationToolSerializer
    authentication_classes = [ActingAsHeaderAuthentication]
    permission_classes = [IsResolvedCaller]

    def get_object(self):
        return get_object_or_404(
            OrganizationTool,
            organization_id=self.kwargs["organization_id"],
            tool_id=self.kwargs["tool_id"],
        )

    def perform_destroy(self, instance):
        if self.request.user.role != UserProfile.Role.ADMIN:
            raise PermissionDenied("Only a platform admin can revoke an organization's tool.")
        instance.delete()


def _create_user_tool_grant(target, tool, caller):
    instance = UserTool(user=target, tool=tool, assigned_by=caller)
    try:
        instance.full_clean()
    except DjangoValidationError as exc:
        raise ValidationError({tool.name: exc.message_dict})
    instance.save()
    return instance


class UserToolView(APIView):
    """GET/POST/PUT/PATCH/DELETE /api/profiles/<profile_id>/tools/

    Manages which tools a coordinator or cde currently holds, all through
    one URL - every write identifies its tool(s) in the body rather than
    the path, since PUT/PATCH need a list anyway to do a full sync.

      GET         - list the profile's current tool grants.
      POST        - grant one or more tools, additive.
                    Body: {"tools": [<tool_id>, ...]}
      PUT / PATCH - replace the profile's tools with exactly this set:
                    grants any missing, revokes any currently-held tool
                    not in the list. {"tools": []} clears every grant.
                    Body: {"tools": [<tool_id>, ...]}
      DELETE      - revoke one or more tools. `tools` is required (no
                    "revoke everything" via an empty body).
                    Body: {"tools": [<tool_id>, ...]}

    Caller rules (same for every write verb here): if the target profile
    is a COORDINATOR, caller must be an ORG_ADMIN of the same
    organization and the organization must already hold each tool
    granted; if the target is a CDE, caller must be a COORDINATOR of the
    same organization and must already hold each tool themself. See
    _check_can_manage_user_tool() and UserTool.clean() for the exact
    rules, enforced here and again at the model layer. Revoking a tool
    from a coordinator cascades to every cde they'd granted it to.
    """

    authentication_classes = [ActingAsHeaderAuthentication]
    permission_classes = [IsResolvedCaller]

    def get_target(self):
        return get_object_or_404(UserProfile, pk=self.kwargs["profile_id"])

    def get_tools(self, request):
        serializer = ToolIdsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return serializer.validated_data["tools"]

    def get(self, request, profile_id):
        target = self.get_target()
        grants = UserTool.objects.filter(user=target)
        return Response(UserToolSerializer(grants, many=True).data)

    def post(self, request, profile_id):
        target = self.get_target()
        _check_can_manage_user_tool(request.user, target)
        tools = self.get_tools(request)
        with transaction.atomic():
            created = [_create_user_tool_grant(target, tool, request.user) for tool in tools]
        return Response(UserToolSerializer(created, many=True).data, status=201)

    def put(self, request, profile_id):
        return self._sync(request, profile_id)

    def patch(self, request, profile_id):
        return self._sync(request, profile_id)

    def _sync(self, request, profile_id):
        target = self.get_target()
        _check_can_manage_user_tool(request.user, target)
        tools = self.get_tools(request)
        wanted_ids = {tool.id for tool in tools}

        with transaction.atomic():
            UserTool.objects.filter(user=target).exclude(tool_id__in=wanted_ids).delete()
            existing_ids = set(
                UserTool.objects.filter(user=target).values_list("tool_id", flat=True)
            )
            for tool in tools:
                if tool.id not in existing_ids:
                    _create_user_tool_grant(target, tool, request.user)

        grants = UserTool.objects.filter(user=target)
        return Response(UserToolSerializer(grants, many=True).data)

    def delete(self, request, profile_id):
        target = self.get_target()
        _check_can_manage_user_tool(request.user, target)
        tools = self.get_tools(request)
        UserTool.objects.filter(user=target, tool__in=tools).delete()
        return Response(status=204)
